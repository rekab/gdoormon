#!/usr/bin/python
"""
This script is released under the GNU GPL v2 license.
"""

import airport_snmp
import argparse
import consolelog
import logging
import leasemonitor
import os
import shelve
import ssh
import sys
import time

SLEEP_SECONDS = 15
CLIENT_DB_PATH = 'client_db.shelve'


def SetupFlags(parser=None):
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


def SetupLogging():
  # Setup presence logging
  fh = logging.FileHandler('presence.log')
  fh.setLevel(logging.INFO)
  formatter = logging.Formatter('%(asctime)s:%(name)s:%(levelname)s] Presence: %(message)s')
  fh.setFormatter(formatter)
  logger = logging.getLogger('presence')
  logger.addHandler(fh)
  return logger


class PresenceMonitor(object):
  def __init__(self, airport, db_file):
    self._airport = airport
    self._db_file = db_file
    self._someone_home = None
    self._log = logging.getLogger('presence')

  def Check(self):
    # TODO: also get clients from dd-wrt assoclist
    airport_clients = airport_snmp.GetData(self._airport)

    # TODO: locking
    # TODO: wrap the shelf object in a __enter__/__exit__ locking class
    db = shelve.open(self._db_file)
    registered_airport_clients = set(airport_clients).intersection(set(db))
    if registered_airport_clients:
      # TODO: announce connections/departures
      logging.log(logging.INFO, '%d registered airport clients: %s',
          len(registered_airport_clients),
          ', '.join(registered_airport_clients))
      self.SetPresenceDetected(True)
    else:
      logging.log(logging.INFO, 'nobody home!')
      self.SetPresenceDetected(False)

    logging.log(logging.DEBUG, 'closing db')
    db.close()
    return self.IsPresenceDetected()

  def IsPresenceDetected(self):
    return self._someone_home

  def SetPresenceDetected(self, b):
    if self._someone_home is None:
      self._log.log(logging.INFO, 'initializing someone_home=%s', b)
      self._someone_home = b
    else:
      if self._someone_home != b:
        self._log.log(logging.INFO, 'toggling someone_home=%s', b)
        self._someone_home = b
        self._Toggle(b)

  def _Toggle(self, b):
    raise NotImplemented('child classes should implement this')


class EspeakPresenceMonitor(PresenceMonitor):
  def _Toggle(self, b):
    if b:
      os.system('/usr/bin/espeak "someone is home"')
    else:
      os.system('/usr/bin/espeak "nobody home"')


def main():
  flags = SetupFlags().parse_args()
  consolelog.SetupRootLogger()
  SetupLogging()

  db = shelve.open(flags.db)
  presence_mon = EspeakPresenceMonitor(flags.airport, db)

  while True:
    presence_mon.Check()
    logging.log(logging.INFO, 'sleeping %d seconds', flags.sleep)
    time.sleep(flags.sleep)


if __name__ == '__main__':
  main()
