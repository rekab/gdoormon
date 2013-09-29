from twisted.persisted import dirdbm

DEFAULT_DB_PATH = '/tmp/presence'

# TODO: path flag
def getDb(db_path=DEFAULT_DB_PATH):
  return dirdbm.DirDBM(db_path)
