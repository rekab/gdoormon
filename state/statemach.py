import fysom
import logging
import os
from twisted.internet import reactor
from twisted.python import log

# When someone is home, how long until alerting about an open door.
DOOR_OPEN_TIMEOUT_SECS = 15 * 60
ALERT_TIMEOUT_SECS = 3 * 60


class StateMachine():
  """States:
  - ok                  - all good
  - nobody_home         - door closed, nobody home
  - door_open           - door open, someone home
  - alerting            - door open, nobody home or open too long
  - door_closing        - close door command sent
  - door_stuck (TODO)
  """

  def __init__(self, broadcaster, doorControl,
      doorOpenTimeoutSecs=DOOR_OPEN_TIMEOUT_SECS,
      alertTimeoutSecs=ALERT_TIMEOUT_SECS,
      callLater=reactor.callLater): 
    self.broadcaster = broadcaster
    self.doorControl = doorControl
    self.doorOpenTimeoutSecs = doorOpenTimeoutSecs
    self.alertTimeoutSecs = alertTimeoutSecs
    self.pendingTimeout = None
    self._callLater = callLater
    self.state = fysom.Fysom({
        'initial': 'ok',
        'events': [
          dict(name='everyone_left', src=['ok', 'nobody_home'], dst='nobody_home'),
          dict(name='everyone_left', src=['door_open', 'alerting'], dst='alerting'),
          dict(name='everyone_left', src='door_closing', dst='door_closing'),

          dict(name='someone_home', src=['ok', 'nobody_home', 'door_closing'], dst='ok'),
          dict(name='someone_home', src='alerting', dst='door_open'),
          dict(name='someone_home', src=['door_open'], dst='door_open'),

          dict(name='door_opened', src=['ok', 'door_open'], dst='door_open'),
          dict(name='door_opened', src=['nobody_home', 'alerting'], dst='alerting'),
          dict(name='door_opened', src='door_closing', dst='door_closing'),

          dict(name='timeout', src=['door_open', 'nobody_home'], dst='alerting'),
          dict(name='timeout', src='alerting', dst='door_closing'),
          #dict(name='timeout', src='door_closing', dst='door_stuck'),

          # Currently only one command: close the door
          dict(name='command_close_door', src=['alerting', 'door_open', 'door_closing'], dst='door_closing'),
          dict(name='command_close_door', src=['nobody_home'], dst='nobody_home'),
          dict(name='command_close_door', src=['ok'], dst='ok'),

          dict(name='door_closed', src=['ok', 'nobody_home', 'alerting', 'door_open', 'door_closing'], dst='ok'),
        ],
        'callbacks': {
          'onchangestate': self.logStateChange,
          'onleave_state_alerting': self.abortNoOpStateTransition,
          'onleave_state_door_closing': self.abortNoOpStateTransition,
          'ondoor_open': self.startDoorOpenTimer,
          'onalerting': self.setAlertCondition,
          'ondoor_closing': self.closeDoor,
          'ondoor_closed': self.handleDoorClosed,
        }})

  def getState(self):
    return self.state.current

  def can(self, event_name):
    return self.state.can(event_name)

  def __getattr__(self, attr):
    if self.can(attr):
      return getattr(self.state, attr)
    raise AttributeError('Unknown attribute "%s"' % attr)

  def logAndSpeakMessage(self, message):
    log.msg(message, logLevel=logging.INFO)
    os.system('espeak "%s" &' % message)

  def logStateChange(self, e):
    log.msg(
        'event %s: changing state: %s -> %s' % (e.event, e.src, e.dst),
        logLevel=logging.INFO)

  def abortNoOpStateTransition(self, e):
    if e.src == e.dst:
      log.msg(
          'event %s: already in state %s, not transitioning' % (e.event, e.src),
          logLevel=logging.INFO)
      return False
    return True

  def startDoorOpenTimer(self, e):
    if self.pendingTimeout:
      assert e.src == 'alerting'
      self.pendingTimeout.cancel()
    self.pendingTimeout = self._callLater(self.doorOpenTimeoutSecs,
        self.timeout)

  def setAlertCondition(self, e):
    if self.pendingTimeout:
      assert e.src == 'door_open'
      self.pendingTimeout.cancel()
      self.pendingTimeout = None

    message = 'DOOR ALERT! Timeout in %s seconds.' % self.alertTimeoutSecs
    self.logAndSpeakMessage(message)
    self.broadcaster.sendAllSubscribers(message)
    self.pendingTimeout = self._callLater(self.alertTimeoutSecs,
        self.timeout)

  def timeout(self):
    assert self.pendingTimeout
    self.pendingTimeout = None
    self.state.timeout()

  def closeDoor(self, e):
    message = 'closing the door'
    if self.pendingTimeout:
      self.pendingTimeout.cancel()
      self.pendingTimeout = None
    self.logAndSpeakMessage(message)
    self.broadcaster.sendAllSubscribers(message)
    self.doorControl.hitButton()
    # TODO: setup a timeout until door_stuck

  def snoozeAlert(self, duration):
    if self.pendingTimeout:
      # TODO: if snoozed, give a 2-minute warning that the snooze will expire
      self.pendingTimeout.reset(duration)
      message = 'snoozed, will timeout in %d seconds' % duration
      self.broadcaster.sendAllSubscribers(message)
      log.msg(message, logLevel=logging.INFO)
      return message
    else:
      return 'no timeout pending'

  def handleDoorClosed(self, e):
    if self.pendingTimeout:
      self.pendingTimeout.cancel()
      self.pendingTimeout = None
      message = 'Door closed, timeout canceled.'
      self.broadcaster.sendAllSubscribers(message)
      log.msg(message, logLevel=logging.INFO)
