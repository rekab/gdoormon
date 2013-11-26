#!/usr/bin/trial

import os
import mox
import statemach
# TODO TODO: straighten out import paths!
from doorcontrol import maestro
#from chatcontrol import xmpp
from twisted.internet import task
from twisted.trial import unittest


class StateMachineTest(unittest.TestCase):
  def tearDown(self):
    self.m.UnsetStubs()

  def setUp(self):
    self.clock = task.Clock()
    self.m = mox.Mox()
    self.m.StubOutWithMock(os, 'system')
    os.system(mox.IgnoreArg()).MultipleTimes().AndReturn(0)

    self.mockBroadcaster = self.m.CreateMockAnything()
    self.mockDoorControl = self.m.CreateMock(maestro.DoorControl)
    self.statemach = statemach.StateMachine(self.mockBroadcaster, self.mockDoorControl,
        callLater=self.clock.callLater, system=os.system)

  def testStartState(self):
    self.assertEquals('ok', self.statemach.getState())

  def testCan(self):
    self.assertTrue(self.statemach.can('command_close_door'))
    self.assertFalse(self.statemach.can('asdf'))

  def expectDoorClosingNotice(self):
    self.mockBroadcaster.sendAllSubscribers(mox.Regex(r'closing the door'))

  def expectAlertNotice(self):
    self.mockBroadcaster.sendAllSubscribers(mox.Regex(r'DOOR ALERT'))

  def expectSnoozeNotice(self):
    self.mockBroadcaster.sendAllSubscribers(mox.Regex(r'snoozed, will timeout'))

  def expectDoorClosedDuringAlertNotice(self):
    self.mockBroadcaster.sendAllSubscribers(mox.Regex(r'Door closed.'))

  def expectDoorClosingNotice(self):
    self.mockBroadcaster.sendAllSubscribers(mox.Regex(r'closing the door'))

  def expectDoorClosing(self):
    self.expectDoorClosingNotice()
    self.mockDoorControl.hitButton()

  def testCloseDoorCommand(self):
    self.expectDoorClosing()

    self.m.ReplayAll()
    self.statemach.door_opened()
    self.statemach.command_close_door()
    self.m.VerifyAll()

  def testSnoozeAlert(self):
    self.expectAlertNotice()
    self.expectSnoozeNotice()

    self.m.ReplayAll()
    self.statemach.everyone_left()
    self.statemach.door_opened()
    self.clock.advance(statemach.ALERT_TIMEOUT_SECS / 2)
    self.assertEquals('', self.statemach.snoozeAlert(100))
    self.clock.advance(99)
    self.m.VerifyAll()

  def testSnoozeAlertAndStillTimeout(self):
    self.expectAlertNotice()
    self.expectSnoozeNotice()
    # TODO: snoozed alerts should have warnings
    self.expectDoorClosing()

    self.m.ReplayAll()
    self.statemach.everyone_left()
    self.statemach.door_opened()
    self.clock.advance(statemach.ALERT_TIMEOUT_SECS / 2)
    self.statemach.snoozeAlert(100)
    self.clock.advance(100)
    self.m.VerifyAll()

  def testSnoozeAlertNoTimeoutPending(self):
    self.assertEquals('no timeout pending', self.statemach.snoozeAlert(10))

  def expectAlertAndDoorClosure(self):
    self.expectAlertNotice()
    self.expectDoorClosingNotice()
    self.mockDoorControl.hitButton()

  def testNobodyHomeDoorOpenAlert(self):
    self.expectAlertAndDoorClosure()

    self.m.ReplayAll()
    self.statemach.everyone_left()
    self.statemach.door_opened()
    self.clock.advance(statemach.ALERT_TIMEOUT_SECS)
    self.m.VerifyAll()

  def testSomeoneHomeDoorOpenTimeoutAlert(self):
    self.expectAlertAndDoorClosure()

    self.m.ReplayAll()
    self.statemach.door_opened()
    self.clock.advance(statemach.DOOR_OPEN_TIMEOUT_SECS)
    self.clock.advance(statemach.ALERT_TIMEOUT_SECS)
    self.m.VerifyAll()

  def testDoorClosedDuringAlert(self):
    self.expectAlertNotice()
    self.expectDoorClosedDuringAlertNotice()

    self.m.ReplayAll()
    self.statemach.everyone_left()
    self.statemach.door_opened()
    self.clock.advance(statemach.ALERT_TIMEOUT_SECS - 10)
    self.statemach.door_closed()
    self.clock.advance(statemach.ALERT_TIMEOUT_SECS)
    self.m.VerifyAll()

  def testPresenceChangedDuringAlert(self):
    # Alert will fire.
    self.expectAlertNotice()
    # Door should close.
    self.expectDoorClosingNotice()
    self.mockDoorControl.hitButton()

    self.m.ReplayAll()
    self.statemach.door_opened()
    self.statemach.everyone_left()
    self.clock.advance(statemach.ALERT_TIMEOUT_SECS - 10)
    self.statemach.someone_home()
    # Alert should still continue and timeout.
    self.clock.advance(11)
    self.m.VerifyAll()

  def testDoorClosedWhileSomeoneHome(self):
    self.mockBroadcaster.sendAllSubscribers(mox.Regex(r'Door closed.'))

    self.m.ReplayAll()
    os.system('pymox MultipleTimes() needs a zero-times option')
    self.statemach.door_opened()
    self.statemach.door_closed()
    self.m.VerifyAll()

  # todo someone_home repeatedly?
