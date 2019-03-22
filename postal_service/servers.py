import email
import envelopes
import imaplib
import logging
import re
import sys
import time

import config

_LOG = logging.getLogger('postal_service')
EMAIL_REGEX = '(?:(.+) )?<?([-\w\.]+@[\w\.]+)>?'


class ImapError(Exception):
  """Error in IMAP request."""


class FatalError(Exception):
  """An error that can't be recovered from."""


class ImapClient(object):

  def __init__(self, username, password):
    self._username = username
    self._password = password
    self._imap = None

  def __getattr__(self, method_name):
    if self._imap is None:
      raise RuntimeError('ImapClient is closed. Client must be used within a '
                         '`with` statement.')

    method = getattr(self._imap, method_name)
    if not callable(method):
      raise RuntimeError('Cannot access attribute %s of ImapClient, expected a'
                         'method name.' % method_name)
    expected_result = 'BYE' if method_name == 'logout' else 'OK'

    def wrapped(*args, **kwargs):
      result, data = method(*args, **kwargs)
      if result != expected_result:
        raise ImapError('Unexpected result %S from IMAP request `%s`.' %
                        (result, method_name))
      return data
    return wrapped

  def __enter__(self):
    self._imap = imaplib.IMAP4_SSL('imap.gmail.com')
    try:
      self.login(self._username, self._password)
    except Exception as e:
      if str(e).find('Lookup failed') != -1:
        raise FatalError('Invalid username: %s@gmail.com' % self._username)
      if str(e).find('Invalid credentials') != -1:
        raise FatalError('Invalid password for account: %s@gmail.com' % self._username)
      raise
    return self

  def __exit__(self, *unused_args):
    try:
      self.close()
      self.logout()
    finally:
      self._imap = None


class Inbox(object):

  def __init__(self, username, password):
    self._client = ImapClient(username, password)
    self._seen_uids = set()

  def _get_all_uids(self):
    return self._client.uid('search', None, 'ALL')[0].split()

  def _get_message_for_uid(self, uid):
    raw_email = self._client.uid('fetch', uid, '(RFC822)')[0][1]
    return email.message_from_string(raw_email)

  def initialize(self):
    with self._client:
      self._client.select('inbox')
      all_uids = self._get_all_uids()
      self._seen_uids.update(all_uids)
      _LOG.info('Inbox: Found %d existing messages.', len(all_uids))

  def get_new_messages(self):
    with self._client:
      self._client.select('inbox')

      all_uids = set(self._get_all_uids())
      new_uids = all_uids - self._seen_uids
      self._seen_uids.update(new_uids)

      for uid in new_uids:
        yield self._get_message_for_uid(uid)


class Sender(object):

  def __init__(self, username, password):
    self.email = username + '@gmail.com'  # TODO: Refactor
    self.gmail = envelopes.GMailSMTP(self.email, password)

  def reply(self, message, reply_body, agent_name):
    subject = 'Re: ' + message['Subject']
    to_field = message['Reply-To'] or message['From']
    to_match = re.match(EMAIL_REGEX, to_field)
    if to_match is None:
      raise RuntimeError('Unknown sender: `%s`' % to_field)
    to_name, to_email = to_match.groups()
    headers = {
        'In-Reply-To': message['Message-ID'],
    }
    self.send(subject, reply_body, agent_name, (to_email, to_name), headers)

  def send(self, subject, body, sender_name, to_addr_or_tuple, headers=None):
    headers = headers or {}
    envelope = envelopes.Envelope(
        from_addr=(self.email, sender_name),
        to_addr=to_addr_or_tuple,
        subject=subject,
        text_body=body,
        headers=headers,
    )
    self.gmail.send(envelope)


class Server(object):

  def __init__(self, account, dispatch, refresh_s):
    self.inbox = Inbox(account.username, account.password)
    self.sender = Sender(account.username, account.password)
    self.dispatch = dispatch
    self.refresh_s = refresh_s

  def start(self):
    # Get initial message UIDs. Don't reply to messages already in the inbox.
    _LOG.info('Server: Starting...')
    self.inbox.initialize()
    _LOG.info('Server: Waiting for new messages...')

    while True:

      found_anything = False

      # Try to read new messages from the inbox.
      try:
        new_messages = self.inbox.get_new_messages()
      except Exception as e:
        _LOG.exception('Server: Error retrieving new messages: %s', e)
        time.sleep(self.refresh_s)
        continue

      for message in new_messages:
        found_anything = True

        _LOG.info('Server: Received new message: %s', message['Subject'])
        reply = self.dispatch.get_reply(message)
        if reply is None:
          _LOG.info('Server: Dispatch gave no reply.')
          continue

        _LOG.info('Server: Sending reply...')
        try:
          self.sender.reply(message, reply.body, reply.name)
        except Exception as e:
          _LOG.exception('Server: Error trying to reply: %s', e)
        else:
          _LOG.info('Server: Sent.')

      if found_anything:
        _LOG.info('Server: Waiting for new messages...')

      time.sleep(self.refresh_s)
