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

import collections
import logging
import re

_LOG = logging.getLogger('postal_service')
EMAIL_REGEX = '(?:(.+) )?<?([-\w\.]+@[\w\.]+)>?'

Message = collections.namedtuple(
    'Message', ['sender_email', 'in_reply_to'])
Reply = collections.namedtuple(
    'Reply', ['body', 'name'])


class Dispatch(object):
  """Dispatches the first agent that accepts the message, or None."""

  def __init__(self, agents):
    self._agents = agents

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

  def _get_message(self, raw_message):
    return Message(
        self._get_sender_email(raw_message),
        raw_message['In-Reply-To'],
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

  def responsd(self, message):
    print message


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
