import logging
import sys

# Never create .pyc files.
sys.dont_write_bytecode = True

import accounts
import agents
import config
import logs
import servers

# TODO: Log like pros.
_LOG = logging.getLogger('postal_service')


def main():
  logs.init_logging()

  # TODO: Support multiple agents with ability to initiate threads.
  dispatch = agents.Dispatch([
    agents.PersonalizedAgent({
      'example@gmail.com': 'First Name',
    }),
    agents.SimpleReplyAgent('Sorry, I do not recognize you.'),
  ])
  account = accounts.Account.from_config(config)
  server = servers.Server(account, dispatch, refresh_s=10.0)

  _LOG.info('Starting server with account %s, refresh_s=10.0', account.username)
  try:
    server.start()
  except Exception as e:
    _LOG.exception('Server exiting with error: %s', e)


if __name__ == '__main__':
  main()