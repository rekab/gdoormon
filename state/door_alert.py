#!/usr/bin/python
"""Alert when nobody is home and the garage door is open."""

import clientmonitor
import consolelog
import comm
import fysom
import gdoormon
import maestro
import logging
import os
import shelve
import time


DOOR_OPEN_SOMEONE_HOME_TIMEOUT = 10 * 60
ALERT_TIMEOUT = 5 * 60


class Timer(object):

  def __init__(self, timeout=0, stubbable_time=time):
    self._start = None
    self._timeout = timeout
    self._time = stubbable_time

  def IsStarted(self):
    return self._start is not None

  def Start(self):
    if self.IsStarted():
      raise RuntimeError('Timer already started')
    self._start = self._time.time()

  def Restart(self, timeout):
    logging.log(logging.INFO, 'restarting timer with timeout=%d', timeout)
    self.Stop()
    self._timeout = timeout
    self.Start()

  def IsTimeoutReached(self):
    logging.log(logging.INFO, 'Checking timeout: start=%s timeout=%s now=%s',
        self._start, self._timeout, self._time.time())
    return self.IsStarted() and (self._time.time() >= self._start + self._timeout)

  def Stop(self):
    self._start = None

  def GetTimeUntilTimeout(self):
    return self._start + self._timeout - self._time.time()


def LogAndSpeakMessage(message):
  logger = logging.getLogger('presence')
  logger.log(logging.INFO, message)
  os.system('espeak "%s"' % message)


def LogStateChange(e):
  logging.log(logging.INFO,
      'event %s: changing state: %s -> %s', e.event, e.src, e.dst)


def AbortNoOpStateTransition(e):
  if e.src == e.dst:
    logging.log(logging.INFO,
        'event %s: already in state %s, not transitioning', e.event, e.src)
    return False
  return True


def StartDoorOpenTimer(e):
  if not AbortNoOpStateTransition(e):
    return
  LogAndSpeakMessage('Starting door open timer')
  e.timer.Restart(DOOR_OPEN_SOMEONE_HOME_TIMEOUT)


def SetAlertCondition(e):
  LogAndSpeakMessage('DOOR ALERT')
  e.communicator.Alert()
  e.timer.Restart(ALERT_TIMEOUT)


def CloseDoor(e):
  LogAndSpeakMessage('closing the door')
  e.communicator.NotifyDoorClosing()
  e.door_control.HitButton()


def BuildStateMachine():
  """Construct a Fysom state machine.

  States:
  - ok                  - all good
  - nobody_home         - door closed, nobody home
  - door_open           - door open, someone home
  - alerting            - door open, nobody home or open too long
  - door_closing        - close door command sent
  - door_stuck (TODO)
  """
  state = fysom.Fysom({
      'initial': 'ok',
      'events': [
        dict(name='everyone_left', src=['ok', 'nobody_home'], dst='nobody_home'),
        dict(name='everyone_left', src=['door_open', 'alerting'], dst='alerting'),
        dict(name='everyone_left', src='door_closing', dst='door_closing'),

        dict(name='someone_home', src=['ok', 'nobody_home', 'door_closing'], dst='ok'),
        dict(name='someone_home', src='alerting', dst='alerting'),
        dict(name='someone_home', src=['door_open'], dst='door_open'),

        dict(name='door_opened', src=['ok', 'door_open'], dst='door_open'),
        dict(name='door_opened', src=['nobody_home', 'alerting'], dst='alerting'),
        dict(name='door_opened', src='door_closing', dst='door_closing'),

        dict(name='timeout', src=['door_open', 'nobody_home'], dst='alerting'),
        dict(name='timeout', src='alerting', dst='door_closing'),
        #dict(name='timeout', src='door_closing', dst='door_stuck'),

        dict(name='close_door_cmd', src=['alerting', 'door_open', 'door_closing'], dst='door_closing'),
        dict(name='close_door_cmd', src=['ok', 'nobody_home'], dst='ok'),

        dict(name='door_closed', src=['ok', 'nobody_home', 'alerting', 'door_open', 'door_closing'], dst='ok'),
      ],
      'callbacks': {
        'onchangestate': LogStateChange,
        'onleave_state_alerting': AbortNoOpStateTransition,
        'onleave_state_door_closing': AbortNoOpStateTransition,
        'ondoor_open': StartDoorOpenTimer,
        'onalerting': SetAlertCondition,
        'ondoor_closing': CloseDoor,
      }})

  return state


def Update(state, presence_mon, door_mon, timer, door_control, communicator):
  try:
    kwds = dict(
        state=state,
        timer=timer,
        door_control=door_control,
        communicator=communicator)

    # TODO: fork the monitors and block on select()
    # only check the door for a few minutes after motion detected
    if door_mon.Check():
      state.door_opened(**kwds)
    else:
      state.door_closed(**kwds)

    if presence_mon.Check():
      state.someone_home(**kwds)
    else:
      state.everyone_left(**kwds)

    if communicator.HasCommand():
      cmd = communicator.PopCommand()
      logging.log(logging.INFO, 'executing command: %s', cmd)
      cmd.Execute(**kwds)

    if timer.IsTimeoutReached():
      timer.Stop()
      state.timeout(**kwds)

  except gdoormon.CommandFailed as e:
    logging.log(logging.ERROR, 'Caught and ignoring: %s', e)


def main():
  consolelog.SetupRootLogger(level=logging.INFO)
  clientmonitor.SetupLogging()
  flags = clientmonitor.SetupFlags().parse_args()

  presence_mon = clientmonitor.EspeakPresenceMonitor(flags.airport, flags.db)
  door_mon = gdoormon.GetMonitor()
  state = BuildStateMachine()
  timer = Timer()
  door_control = maestro.DoorControl(maestro.PololuMicroMaestro()) 
  communicator = comm.Communicator()

  while True:
    Update(state, presence_mon, door_mon, timer, door_control, communicator)
    time.sleep(10)

  #Loop(flags.sleep, presence_mon, door_mon, state)


if __name__ == '__main__':
  main()
