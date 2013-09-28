import random
from twisted.python import log

def randomDoorState(statemach):
  if random.choice([True, False]):
    log.msg('faking that the door is open')
    statemach.door_opened()
  else:
    log.msg('faking that the door is closed')
    statemach.door_closed()
