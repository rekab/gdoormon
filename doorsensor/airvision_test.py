#!/usr/bin/python

import airvision
import mox
import unittest


class DoorMonitorTest(unittest.TestCase):
  def setUp(self):
    self.m = mox.Mox()
    self.mock_checker = self.m.CreateMock(airvision.GarageDoorChecker)
    self.monitor = airvision.GarageDoorMonitor(self.mock_checker)

  def testCheckOnce(self):
    self.mock_checker.IsDoorOpen().AndReturn(True)
    self.m.ReplayAll()
    self.assertTrue(self.monitor.Check())
    self.m.VerifyAll()

  def testCheckNegative(self):
    self.mock_checker.IsDoorOpen().AndReturn(False)
    self.mock_checker.IsDoorOpen().AndReturn(False)
    self.mock_checker.IsDoorOpen().AndReturn(False)
    self.m.ReplayAll()
    self.assertFalse(self.monitor.Check())
    self.assertFalse(self.monitor.Check())
    self.assertFalse(self.monitor.Check())
    self.m.VerifyAll()


class DoorCheckerTest(unittest.TestCase):
  def setUp(self):
    self.m = mox.Mox()

if __name__ == '__main__':
  unittest.main()
