from twisted.python import log

class FakePololuMicroMaestro(object):
  def setAngle(self, angle):
    log.msg('servo angle changed to %s' % angle)

  def goHome(self):
    log.msg('servo returned to home')
