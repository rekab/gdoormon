"""Garage door button presser.

Requires the pololu micro maestro, set in "USB Dual Port" mode.
"""
import consolelog
import logging
import serial
import time

IMPINGE_ANGLE = 170
RETRACT_ANGLE = 10


class PololuMicroMaestro(object):
  """http://afflator.ontopoeticmachines.org/post/9"""
  def __init__(self, port='/dev/ttyACM0'):
      self.ser = serial.Serial(port=port)

  def SetAngle(self, angle, channel=0):
    """Set the target angle of the servo.  This is converted into "quarter
    microseconds", i.e., the pulse width necessary to get to that angle (and
    thus it's between 1.0ms and 2.0ms in increments of 0.25us).  Whew!"""
    logging.log(logging.INFO, 'SetAngle(%s)', angle)
    minAngle = 0.0
    maxAngle = 180.0
    # these numbers, in quarter microseconds, taken from the code here:
    # http://forum.pololu.com/viewtopic.php?t=2380#p10697
    minTarget = 256.0
    maxTarget = 13120.0
    scaledValue = int((angle / ((maxAngle - minAngle) / (maxTarget - minTarget))) + minTarget)
    commandByte = chr(0x84)
    channelByte = chr(channel)
    lowTargetByte = chr(scaledValue & 0x7F)
    highTargetByte = chr((scaledValue >> 7) & 0x7F)
    command = commandByte + channelByte + lowTargetByte + highTargetByte
    self.ser.write(command)
    self.ser.flush()

  def GoHome(self):
    """Set all servos to home position."""
    logging.log(logging.INFO, 'GoHome()')
    self.ser.write(chr(0xA2))

  def Close(self):
    self.ser.close()


class DoorControl(object):
  def __init__(self, p):
    self._p = p
    self._Retract()

  def _Retract(self):
    logging.log(logging.INFO, '<- retract')
    self._p.SetAngle(IMPINGE_ANGLE)
    time.sleep(.5)
    self._p.GoHome()

  def _Impinge(self):
    logging.log(logging.INFO, 'impinge ->')
    self._p.SetAngle(RETRACT_ANGLE)

  def HitButton(self):
    self._Impinge()
    time.sleep(.5)
    self._Retract()


if __name__ == '__main__':
  consolelog.SetupRootLogger()
  p = PololuMicroMaestro()
  dc = DoorControl(p)
  while True:
    dc.HitButton()
    time.sleep(1)
