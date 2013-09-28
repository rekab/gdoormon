import random
from twisted.python import log

def randomPresence(statemach):
  if random.choice([True, False]):
    log.msg('faking that everyone left')
    statemach.everyone_left()
  else:
    log.msg('faking someone is home')
    statemach.someone_home()
