import logging

_LOG = logging.getLogger('postal_service')


def init_logging():
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
