import cgi
import logging
import re
import shelve

from presence import airport_clientmonitor

from twisted.internet import defer
from twisted.internet import error
from twisted.internet import protocol
from twisted.internet import reactor
from twisted.python import log
from twisted.web import resource
from twisted.web import server
from twisted.python import failure

ARP_BIN = '/usr/sbin/arp'

class CannotGetIp(failure.Failure):
  pass


class GetMacForIpProcessProtocol(protocol.ProcessProtocol):
  """Calls arp -n <p> address to get the mac address of a connected ip.
  
  In retrospect, writing this as an asynchronous process is overkill.
  """
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
    """Determine if the process succeded or failed. On success, calls the
    deferred callback with a lowercased string of the mac address obtained."""
    if isinstance(status.value, error.ProcessTerminated):
      msg = 'Process exited with non-zero status code: %d' % status.value.exitCode
      log.msg(msg, logLevel=logging.CRITICAL)
      self._d.errback(CannotGetIp(msg))
      return

    # Parse the output
    lines = ''.join(self._data).split('\n')
    if len(lines) != 3:
      msg = 'Cannot parse arp response: <pre>%s</pre>' % '\n'.join(lines)
      log.msg(msg, logLevel=logging.CRITICAL)
      self._d.errback(CannotGetIp(msg))
      return

    parts = re.split(r'\s+', lines[1])
    if len(parts) < 3:
      msg = 'malformed line: %s' % lines[1]
      log.msg(msg, logLevel=logging.CRITICAL)
      self._d.errback(CannotGetIp(msg))
      return
    self._d.callback(parts[2].lower())


class RegistrationResource(resource.Resource):
  """Base class for registration web resources."""

  def handleLookupError(self, failure, request):
    """Called when the mac address looked fails."""
    request.write('failed to lookup your mac: %s' % failure)

  def handleLookup(self, mac, request):
    """Called when the mac address looked completes."""
    raise NotImplemented('uhh')

  def render_POST(self, request):
    return self.render_GET(request)

  def render_GET(self, request):
    """Takes a request, spawns an arp lookup subprocess."""
    if not request.path.endswith('/'):
      request.setResponseCode(404)
      return 'That resource is not here.'

    d = defer.Deferred()
    d.addCallbacks(self.handleLookup, self.handleLookupError,
        callbackArgs=(request,), errbackArgs=(request,))
    d.addBoth(self.done, request)
    lookupProcess = GetMacForIpProcessProtocol(request.getClientIP(), d)
    reactor.spawnProcess(lookupProcess, lookupProcess.getExecutable(),
        lookupProcess.getArgs())
    return server.NOT_DONE_YET

  def done(self, reason, request):
    if isinstance(reason, failure.Failure):
      log.err()
      request.write('Internal error.')
    request.finish()


class RegistrationLookup(RegistrationResource):
  isLeaf = True

  def __init__(self, form_action):
    RegistrationResource.__init__(self)
    self._form_action = form_action

  def handleLookup(self, mac, request):
    """Displays the form to register or unregister a mac address.

    Called when the mac address lookup subprocess completes.

    Args:
      mac: mac address as string
      request: request object
    """
    request.write('Your MAC address is: %s<p>' % mac)
    db = None
    try:
      db = shelve.open(airport_clientmonitor.CLIENT_DB_PATH)
      request.write('<form action="%s" method="post">' % self._form_action)
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


class RegistrationUpdate(RegistrationResource):
  isLeaf = True

  def handleLookup(self, mac, request):
    """Register or unregister a mac address.

    Called when the mac address lookup subprocess completes.
    """
    postvars = request.args
    if ('action' not in postvars or 
        postvars['action'][0] not in ['register', 'unregister']):
      request.setResponseCode(500)
      request.write('missing args')
      return
    # TODO: refactor db manipulations to a module. Use twisted's DirDBM.
    db = None
    try:
      db = shelve.open(airport_clientmonitor.CLIENT_DB_PATH)
      request.write('Your divice (%s) is ' % mac)
      if postvars['action'][0] == 'register':
        db[mac] = request.getClientIP()
      else:
        if mac in db:
          del db[mac]
        request.write('un')
      request.write('registered.')
    finally:
      if db is not None:
        db.close()


def GetRegistrationResource():
  root = resource.Resource()
  lookup = RegistrationLookup('/register/')
  root.putChild('', lookup)
  root.putChild('register', RegistrationUpdate())
  return root
