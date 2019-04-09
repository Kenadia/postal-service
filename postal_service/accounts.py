import logging

_LOG = logging.getLogger('postal_service')


class Account(object):

  def __init__(self, username, password):
    self.username = username
    self.password = password

  @classmethod
  def from_config(cls, config):
    if not isinstance(config, dict):
      config = config.__dict__
    return cls(config['username'], config['password'])
