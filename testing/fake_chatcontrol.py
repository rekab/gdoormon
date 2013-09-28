import random
from twisted.python import log

class FakeChatBroadcastProtocol(object):
  def sendAllSubscribers(self, text):
    log.msg('broadcasting: %s' % text)


class FakeChatCommandReceiverProtocol(object):
  possible_events = [('snoozeAlert', (1,)), ('command_close_door', ())]

  def __init__(self, statemach):
    self.statemach = statemach

  def pretendSomethingHappened(self):
    event = random.choice(self.possible_events)
    func = event[0]
    args = event[1]
    log.msg('calling statemach.%s(%s)' % (func, args))
    ret = getattr(self.statemach, func)(*args)
    log.msg('statemach.%s(%s) returned: %s' % (func, args, repr(ret)))
