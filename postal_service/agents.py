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

MessageInfo = collections.namedtuple(
    'MessageInfo', ['sender_email', 'in_reply_to'])
Reply = collections.namedtuple(
    'Reply', ['body', 'name'])


class Dispatch(object):
  """Dispatches the first agent that accepts the message, or None."""

  def __init__(self, agents):
    self._agents = agents

  def _get_sender_email(self, message):
    match = re.match(EMAIL_REGEX, message['From'])
    if match:
      return match.groups()[1]
    _LOG.warn('Dispatch: Failed to parse sender field `%s`', message['From'])

  def _get_message_info(self, message):
    return MessageInfo(
        self._get_sender_email(message),
        message['In-Reply-To'],
    )

  def _get_agent(self, message_info):
    for agent in self._agents:
      if agent.accepts(message_info):
        return agent

  def get_reply(self, message):
    message_info = self._get_message_info(message)
    agent = self._get_agent(message_info)

    if not agent:
      return

    reply = agent.respond(message_info)

    if reply is None:
      return

    return Reply(reply, agent.display_name)


class BaseAgent(object):
  display_name = 'Postal Service'

  def accepts(self, message_info):
    raise NotImplementedError

  def respond(self, message_info):
    raise NotImplementedError


class NoReplyAgent(BaseAgent):

  def accepts(self, _message_info):
    return True

  def respond(self, _message):
    pass


class LoggingAgent(NoReplyAgent):

  def responsd(self, message):
    print message


class EchoAgent(BaseAgent):

  def __init__(self, known_users):
    self.known_users = known_users

  def accepts(self, message_info):
    return message_info.sender_email in known_users

  def respond(self, body, message_info):
    return 'Echo: ' + body


class SimpleReplyAgent(BaseAgent):

  def __init__(self, reply):
    self.reply = reply

  def accepts(self, message_info):
    return True

  def respond(self, message_info):
    return self.reply


class PersonalizedAgent(BaseAgent):

  def __init__(self, users):
    self.users = users

  def accepts(self, message_info):
    return message_info.sender_email in self.users

  def respond(self, message_info):
    return 'Hello, %s.' % self.users[message_info.sender_email]
