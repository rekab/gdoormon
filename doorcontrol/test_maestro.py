#!/usr/bin/trial

from twisted.internet import task
from twisted.trial import unittest
import maestro
import mox
import time

class DoorControlTest(unittest.TestCase):
  def setUp(self):
    self.m = mox.Mox()
    self.mock_micro_maestro = self.m.CreateMock(maestro.PololuMicroMaestro)
    self.clock = task.Clock()
    self.control = maestro.DoorControl(
        self.mock_micro_maestro, callLater=self.clock.callLater)
#    self.patch(time, 'sleep', self.mockSleep)
#    self.sleeps = []
#
#  def mockSleep(self, duration):
#    self.sleeps.append(duration)

  def testHitButton(self):
    self.mock_micro_maestro.setAngle(maestro.IMPINGE_ANGLE)
    self.mock_micro_maestro.setAngle(maestro.RETRACT_ANGLE)
    self.mock_micro_maestro.goHome()
    self.m.ReplayAll()
    self.control.hitButton()
    self.clock.advance(1)
    self.clock.advance(1)
    self.m.VerifyAll()
