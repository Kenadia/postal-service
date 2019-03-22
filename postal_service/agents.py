# An agent is responsible for deciding when and how to send and reply to emails.
#
# Agents have memory, allowing them to recognize incoming emails in the context
# of threads. For example, an agent may recognize an email as a reply to
# something the agent said earlier.
#
# An agent starts with an empty memory when the server starts.
#
# Agents do not share information with one another, but they may be coordinated
# by a dispatch.

# TODO: Implement SMS proxy agent.
# TODO: Implement framework for proxy agents.
# TODO: Implement framework for conversation agents.

from __future__ import print_function

import collections
import logging
import re
import tempfile

_LOG = logging.getLogger('postal_service')

ATTACHMENTS_DIR = 'attachments'
EMAIL_REGEX = '(?:(.+) )?<?([-\w\.]+@[\w\.]+)>?'

Message = collections.namedtuple(
    'Message', ['subject', 'body', 'sender_email', 'in_reply_to', 'attachments'])
Reply = collections.namedtuple(
    'Reply', ['body', 'name'])


class Dispatch(object):
  """Dispatches the first agent that accepts the message, or None."""

  def __init__(self, agents):
    self._agents = agents
    self.tempfiles = []

  def _get_sender_email(self, raw_message):
    match = re.match(EMAIL_REGEX, raw_message['From'])
    if match:
      return match.groups()[1]
    _LOG.warn(
        'Dispatch: Failed to parse sender field `%s`',
        raw_message['From']
    )

  def _get_message_body(self, raw_message):
    if raw_message.get_content_type() == 'text/plain':
      return raw_message.get_payload()
    if raw_message.get_content_maintype() == 'multipart':
      for part in raw_message.get_payload():
        if part.get_content_type() == 'text/plain':
          return part.get_payload()
    _LOG.warn('Inbox: Got a message without any plain text.')
    return ''

  def _get_attachments(self, raw_message):
    for part in raw_message.walk():
      if part.get_content_maintype() == 'multipart':
        continue
      if part.get('Content-Disposition') is None:
        continue

      filename = part.get_filename()
      data = part.get_payload(decode=True)

      if not data:
        continue

      f = tempfile.NamedTemporaryFile()
      f.write(data)
      f.flush()
      yield f.name

      # Keep the file open and available until the server shuts down.
      self.tempfiles.append(f)

  def _get_message(self, raw_message):
    return Message(
        raw_message['Subject'],
        self._get_message_body(raw_message),
        self._get_sender_email(raw_message),
        raw_message['In-Reply-To'],
        list(self._get_attachments(raw_message)),
    )

  def _get_agent(self, message):
    for agent in self._agents:
      if agent.accepts(message):
        return agent

  def get_reply(self, raw_message):
    message = self._get_message(raw_message)
    agent = self._get_agent(message)

    if not agent:
      return

    reply = agent.respond(message)

    if reply is None:
      return

    return Reply(reply, agent.display_name)


class BaseAgent(object):
  display_name = 'Postal Service'

  def accepts(self, message):
    raise NotImplementedError

  def respond(self, message):
    raise NotImplementedError


class NoReplyAgent(BaseAgent):

  def accepts(self, _message):
    return True

  def respond(self, _message):
    pass


class LoggingAgent(NoReplyAgent):

  def respond(self, message):
    print(message)


class EchoAgent(BaseAgent):

  def __init__(self, known_users):
    self.known_users = known_users

  def accepts(self, message):
    return message.sender_email in known_users

  def respond(self, body, message):
    return 'Echo: ' + body


class SimpleReplyAgent(BaseAgent):

  def __init__(self, reply):
    self.reply = reply

  def accepts(self, message):
    return True

  def respond(self, message):
    return self.reply


class PersonalizedAgent(BaseAgent):

  def __init__(self, users):
    self.users = users

  def accepts(self, message):
    return message.sender_email in self.users

  def respond(self, message):
    return 'Hello, %s.' % self.users[message.sender_email]
