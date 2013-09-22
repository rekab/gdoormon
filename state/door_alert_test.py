import clientmonitor
import consolelog
import door_alert
import gdoormon
import os
import maestro
import mox
import time
import unittest


class FakeTimeModule(object):

  def __init__(self, t):
    self.t = t

  def SetTime(self, t):
    self.t = t

  def time(self):
    return self.t


class StateMachineTest(unittest.TestCase):

  def tearDown(self):
    self.m.UnsetStubs()

  def setUp(self):
    self.m = mox.Mox()
    self.m.StubOutWithMock(os, 'system')
    os.system(mox.IgnoreArg()).MultipleTimes().AndReturn(0)

    # XXX: would like to stub out time, but doing so breaks the unittest module
    #self.m.StubOutWithMock(time, 'time')
    self.fake_time = FakeTimeModule(0.0)
    self.timer = door_alert.Timer(door_alert.DOOR_OPEN_SOMEONE_HOME_TIMEOUT,
        self.fake_time)
    self.mock_door_control = self.m.CreateMock(maestro.DoorControl)
    self.mock_presence_mon = self.m.CreateMock(clientmonitor.EspeakPresenceMonitor)
    self.mock_door_mon = self.m.CreateMock(gdoormon.GarageDoorMonitor)
    self.mock_communicator = self.m.CreateMockAnything()
    self.state = door_alert.BuildStateMachine(self.timer)

  def testSomeoneHomeDoorOpenTimeoutAlert(self):
    # Setup three phases:
    # First phase we detect the door is open.
    self.mock_door_mon.Check().AndReturn(True)        # door is open
    self.mock_presence_mon.Check().AndReturn(True)    # someone is home
    self.mock_communicator.HasCommand().AndReturn(False)

    # Second phase the timer expires.
    self.mock_door_mon.Check().AndReturn(True)        # door is open
    self.mock_presence_mon.Check().AndReturn(True)    # someone is home
    self.mock_communicator.HasCommand().AndReturn(False)
    # Hit the "door open too long" timeout
    self.mock_communicator.Alert()                    # should alert

    # Third phase the alert timeout expires
    self.mock_door_mon.Check().AndReturn(True)        # door is open
    self.mock_presence_mon.Check().AndReturn(True)    # someone is home
    self.mock_communicator.HasCommand().AndReturn(False)
    # Hit the alert timeout
    self.mock_communicator.NotifyDoorClosing()
    self.mock_door_control.HitButton()                # Should attempt to close the door

    self.m.ReplayAll()
    # Phase 1
    door_alert.Update(self.state, self.mock_presence_mon, self.mock_door_mon,
        self.timer, self.mock_door_control, self.mock_communicator)
    # Door open timer should be started now
    self.assertTrue(self.timer.IsStarted())

    # Phase 2
    # Time moves forward
    self.fake_time.SetTime(door_alert.DOOR_OPEN_SOMEONE_HOME_TIMEOUT)
    door_alert.Update(self.state, self.mock_presence_mon, self.mock_door_mon,
        self.timer, self.mock_door_control, self.mock_communicator)

    # Phase 3
    # Time moves forward
    self.fake_time.SetTime(door_alert.DOOR_OPEN_SOMEONE_HOME_TIMEOUT +
        door_alert.ALERT_TIMEOUT)
    door_alert.Update(self.state, self.mock_presence_mon, self.mock_door_mon,
        self.timer, self.mock_door_control, self.mock_communicator)
    self.m.VerifyAll()

  def testNobodyHomeDoorOpenAlert(self):
    # First phase: we detect the door is open.
    self.mock_door_mon.Check().AndReturn(True)        # door is open
    self.mock_presence_mon.Check().AndReturn(False)   # nobody is home
    self.mock_communicator.Alert()                    # should alert
    self.mock_communicator.HasCommand().AndReturn(False)

    # Second phase: the alert timeout expires.
    self.mock_door_mon.Check().AndReturn(True)        # door is open
    self.mock_presence_mon.Check().AndReturn(False)   # nobody is home
    self.mock_communicator.HasCommand().AndReturn(False)
    # Hit the alert timeout
    self.mock_communicator.NotifyDoorClosing()
    self.mock_door_control.HitButton()                # Should attempt to close the door

    self.m.ReplayAll()
    # Phase 1
    door_alert.Update(self.state, self.mock_presence_mon, self.mock_door_mon,
        self.timer, self.mock_door_control, self.mock_communicator)
    # Alert timer should be started now
    self.assertTrue(self.timer.IsStarted())

    # Phase 2
    # Time moves forward
    self.fake_time.SetTime(door_alert.ALERT_TIMEOUT)
    door_alert.Update(self.state, self.mock_presence_mon, self.mock_door_mon,
        self.timer, self.mock_door_control, self.mock_communicator)
    self.m.VerifyAll()

  def testSnoozeAlert(self):
    pass

  def testAlertUnackedDoorClosedAfterTimeout(self):
    pass

  def testAlertAckedDoorClosed(self):
    pass

  def testDoorClosedDuringAlert(self):
    pass

  def testPresenceChangedDuringAlert(self):
    pass


if __name__ == '__main__':
  consolelog.SetupRootLogger()
  unittest.main()
