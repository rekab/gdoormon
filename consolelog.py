import logging

def SetupRootLogger(level=logging.DEBUG):
  logger = logging.getLogger()
  logger.setLevel(level)
  ch = logging.StreamHandler()
  ch.setLevel(level)
  formatter = logging.Formatter('%(asctime)s:%(name)s:%(levelname)s] %(message)s')
  ch.setFormatter(formatter)
  logger.addHandler(ch)
