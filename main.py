import sys

# Never create .pyc files.
sys.dont_write_bytecode = True

import accounts
import agents
import config
import logging
import servers

# TODO: Log like pros.
_LOG = logging.getLogger('postal_service')


def init_logging()
  formatter = logging.Formatter(
      '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
  file_handler = logging.FileHandler('postal_service.log')
  file_handler.setLevel(logging.DEBUG)
  file_handler.setFormatter(formatter)
  console_handler = logging.StreamHandler()
  console_handler.setLevel(logging.DEBUG)
  console_handler.setFormatter(formatter)
  _LOG.setLevel(logging.DEBUG)
  _LOG.addHandler(file_handler)
  _LOG.addHandler(console_handler)


def main():
  init_logging()

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
