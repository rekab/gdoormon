import logging
import re

from twisted.internet import defer
from twisted.internet import error
from twisted.internet import protocol
from twisted.internet import reactor
from twisted.python import log
from twisted.web import resource
from twisted.web import server
from twisted.web import error as web_error
from twisted.python import failure

ARP_BIN = '/usr/sbin/arp'

class CannotGetIp(failure.Failure):
  pass


class GetMacForIpProcessProtocol(protocol.ProcessProtocol):
  """Calls arp -n <p> address to get the mac address of a connected ip."""
  def __init__(self, ip, d):
    self._ip = ip
    self._d = d
    self._data = []

  def connectionMade(self):
    self.transport.closeStdin()

  def getExecutable(self):
    return ARP_BIN

  def getArgs(self):
    return [ARP_BIN, '-n', self._ip]

  def outReceived(self, data):
    self._data.append(data)

  def processEnded(self, status):
    if isinstance(status.value, error.ProcessTerminated):
      msg = 'Process exited with non-zero status code: %d' % status.value.exitCode
      log.error(msg, logLevel=logging.CRITICAL)
      self._d.errback(CannotGetIp(msg))
      return

    # Parse the output
    lines = ''.join(self._data).split('\n')
    if len(lines) != 3:
      msg = 'cmd returned: %s' % lines
      log.msg(msg, logLevel=logging.CRITICAL)
      self._d.errback(CannotGetIp(msg))
      return

    parts = re.split(r'\s+', lines[1])
    if len(parts) < 3:
      msg = 'malformed line: %s' % lines[1]
      log.msg(msg, logLevel=logging.CRITICAL)
      self._d.errback(CannotGetIp(msg))
      return
    self._d.callback(parts[2])


class Registration(resource.Resource):
  isLeaf = True

  def handleError(self, failure, request):
    request.write('failed to lookup your mac: %s' % failure)

  def render_GET(self, request):
    if request.path.endswith('favicon.ico'):
      return web_error.NoResource()

    d = defer.Deferred()
    d.addCallbacks(self.handleLookup, self.handleError, callbackArgs=(request,),
        errbackArgs=(request,))
    d.addBoth(self.done, request)
    lookupProcess = GetMacForIpProcessProtocol(request.getClientIP(), d)
    reactor.spawnProcess(lookupProcess, lookupProcess.getExecutable(),
        lookupProcess.getArgs())
    return server.NOT_DONE_YET

  def handleLookup(self, mac, request):
    request.write('FYI your MAC address is: %s' % mac)
    db = None
    try:
      db = shelve.open(clientmonitor.CLIENT_DB_PATH)
      request.write('<form action="/register" method="post">')
      if mac in db:
        request.write('You are registered.')
        request.write('<input type="hidden" name="action" value="unregister">')
        request.write('<input type="submit" value="unregister">')
      else:
        request.write('You are not registered.')
        request.write('<input type="hidden" name="action" value="register">')
        request.write('<input type="submit" value="register">')
      request.write('</form>')
    finally:
      if db is not None:
        db.close()

  def done(self, reason, request):
    request.finish()

