#!/usr/bin/python
#
# Simple admin script to edit the clientdb.
#

import argparse
import clientmonitor
import logging
import pprint
from presence import clientdb

def List(d, key):
  if key:
    pprint.pprint(d[key])
  else:
    print '\n'.join(d.keys())

def Add(d, key):
  # TODO: specify a value
  d[key] = 1
  print 'added %s' % key

def Del(d, key):
  del d[key]
  print 'deleted %s' % key

if __name__ == '__main__':
  COMMANDS = {
      'add': Add,
      'list': List,
      'del': Del
  }

  parser = argparse.ArgumentParser(description='Manipulate a client db')
  parser.add_argument('--command', help='list, add, or del', required=True)
  parser.add_argument('--key', help='key to list, add, or del')
  # TODO: this flag should come from clientdb
  parser.add_argument('--db', help='db path', default=clientdb.DEFAULT_DB_PATH)
  flags = parser.parse_args()

  if flags.command not in COMMANDS:
    logging.log(logging.FATAL, 'unknown command: %s', flags.command)

  d = clientdb.getDb(flags.db)
  COMMANDS[flags.command](d, flags.key)

