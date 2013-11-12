#!/usr/bin/python
"""
This script is released under the GNU GPL v2 license.

toggle = airport_clientmonitor.StatemachToggle(statemach)
monitor = airport_clientmonitor.PresenceMonitor(airport_hostname, clients, toggle)
pressence_service = internet.TimerService(15, monitor.check)
"""

import airport_snmp
import argparse
import os
import sys
import time
from presence import clientdb
from twisted.python import log

SLEEP_SECONDS = 15


class PresenceMonitor(object):
  def __init__(self, airportHostname, db, toggleCallback):
    self._airportHostname = airportHostname
    self._db = db
    self._someone_home = None
    self._toggleCallback = toggleCallback
    #self._log = logging.getLogger('presence')

  def check(self):
    log.msg('Polling for airport clients.')
    # TODO: getData should be a callback
    airport_clients = airport_snmp.getData(self._airportHostname)

    registered_airport_clients = set(airport_clients
        ).intersection(set(self._db.keys()))
    if registered_airport_clients:
      # TODO: announce connections/departures
      log.msg('%d registered airport clients: %s' % (
              len(registered_airport_clients),
              ', '.join(registered_airport_clients)))
      self.setPresenceDetected(True)
    else:
      log.msg('nobody home!')
      self.setPresenceDetected(False)

    return self.isPresenceDetected()

  def isPresenceDetected(self):
    return self._someone_home

  def setPresenceDetected(self, b):
    if self._someone_home is None:
      log.msg('initializing someone_home=%s' % b)
      self._someone_home = b
    else:
      if self._someone_home != b:
        log.msg('toggling someone_home=%s' % b)
        self._someone_home = b
        self._toggleCallback(b)


class StatemachToggle(object):
  def __init__(self, statemach):
    self.statemach = statemach

  def __call__(self, presence):
    if presence:
      self.statemach.someone_home()
    else:
      self.statemach.everyone_left()


def espeakToggle(b):
  if b:
    os.system('/usr/bin/espeak "someone is home"')
  else:
    os.system('/usr/bin/espeak "nobody home"')


def setupFlags(parser=None):
  """Setup an argparse.ArgumentParser.

  Args:
    parser: argparse.ArgumentParser to configure (optional)

  Returns:
    A configured argparse.ArgumentParser.
  """
  if not parser:
    parser = argparse.ArgumentParser(description='Trigger stuff when clients connect')
  parser.add_argument('--sleep', help='Polling interval sleep.',
      default=SLEEP_SECONDS)
  parser.add_argument('--airport', help='airport hostname', default='hoth')
  parser.add_argument('--db', help='db path', default=CLIENT_DB_PATH)
  return parser


def setupLogging():
  # Setup presence logging
  fh = logging.FileHandler('presence.log')
  fh.setLevel(logging.INFO)
  formatter = logging.Formatter('%(asctime)s:%(name)s:%(levelname)s] Presence: %(message)s')
  fh.setFormatter(formatter)
  logger = logging.getLogger('presence')
  logger.addHandler(fh)
  return logger


def main():
  flags = setupFlags().parse_args()
  setupLogging()

  db = clientdb.getDb()
  presence_mon = PresenceMonitor(flags.airport, db, toggle)

  while True:
    presence_mon.Check()
    log.msg('sleeping %d seconds' % flags.sleep)
    time.sleep(flags.sleep)


if __name__ == '__main__':
  main()
