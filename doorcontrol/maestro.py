"""Garage door button presser.

Requires a Pololu Micro Maestro set in "USB Dual Port" mode.
"""
import serial
from twisted.internet import reactor
from twisted.python import log

PRESS_DURATION = .5
IMPINGE_ANGLE = 0
RETRACT_ANGLE = 60


class PololuMicroMaestro(object):
  """http://afflator.ontopoeticmachines.org/post/9"""
  def __init__(self, port='/dev/ttyACM0'):
      self.ser = serial.Serial(port=port)

  def setAngle(self, angle, channel=0):
    """Set the target angle of the servo.  This is converted into "quarter
    microseconds", i.e., the pulse width necessary to get to that angle (and
    thus it's between 1.0ms and 2.0ms in increments of 0.25us).  Whew!"""
    log.msg('SetAngle(%s)' % angle)
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

  def goHome(self):
    """Set all servos to home position."""
    log.msg('GoHome()')
    self.ser.write(chr(0xA2))

  def close(self):
    self.ser.close()

  def __del__(self):
    self.close()


class DoorControl(object):
  def __init__(self, p, pressDuration=PRESS_DURATION, callLater=reactor.callLater,
      impingeAngle=IMPINGE_ANGLE, retractAngle=RETRACT_ANGLE):
    self._p = p
    self._pressDuration = pressDuration
    self._callLater = callLater
    self._impingeAngle = impingeAngle
    self._retractAngle = retractAngle

  def _impinge(self):
    log.msg('impinge ->')
    self._p.setAngle(self._impingeAngle)

  def _retract(self):
    log.msg('<- retract')
    self._p.setAngle(self._retractAngle)
    self._callLater(self._pressDuration, self._idle)
  
  def _idle(self):
    log.msg('idle')
    self._p.goHome()

  def hitButton(self):
    self._impinge()
    self._callLater(self._pressDuration, self._retract)


#if __name__ == '__main__':
#  import time
#  p = PololuMicroMaestro()
#  dc = DoorControl(p)
#  while True:
#    dc.HitButton()
#    time.sleep(1)
