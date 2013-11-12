"""
Polls the Arduino sensor server for the status of the door.

toggle = arduino_client.StatemachToggle(statemach)
monitor = arduino_client.DoorSensor(toggle, hostname, port, threshold)
pressence_service = internet.TimerService(15, monitor.check)
"""

ARDUINO_HOSTNAME = 'arduino-gdoor'
ARDUINO_PORT = 80
THRESHOLD_CM = 10   # anything over 10cm is "open"
REQUEST_PATH = '/'

from twisted.internet import reactor
from twisted.python import log
from twisted.web import client
from twisted.web import http
from twisted.internet import protocol


class DoorSensor(object):
  def __init__(self, toggle, hostname=ARDUINO_HOSTNAME, port=ARDUINO_PORT,
      threshold=THRESHOLD_CM, requestPath=REQUEST_PATH):
    self.toggle = toggle
    self.hostname = hostname
    self.port = port
    self.threshold = threshold
    self.requestPath = requestPath

  def check(self):
    """Check if the door is open by making an HTTP request to the Arduino.

    Args:
      hostname: host to connect to
      port: port to connect to
      threshold: distance to the door

    Returns:
      boolean - door is open or not
    """
    log.msg('Polling %s for distance.' % self.hostname)
    agent = client.Agent(reactor)
    d = agent.request('GET', 'http://%s%s' % (self.hostname, self.requestPath));
    d.addCallback(self._handleResponse)
    d.addErrback(self._handleError)

  def _handleResponse(self, response):
    response.deliverBody(DoorMeasurementProtocol(self.toggle, self.threshold))

  def _handleError(self, response):
    log.msg('Got: %s' % response)


class DoorMeasurementProtocol(protocol.Protocol):

  def __init__(self, toggle, threshold):
    self.toggle = toggle
    self.threshold = threshold

  def dataReceived(self, data):
    log.msg('threshold=%s, read from server: %s' % (self.threshold, repr(data)))
    try:
      try:
        distance = int(data)
        if distance > self.threshold:
          log.msg('Door is open.')
          self.toggle(True)
        else:
          log.msg('Door is closed.')
          self.toggle(False)
      except ValueError as e:
        log.msg('Bad data from the server: %s' % repr(data))
    except Exception as e:
      import traceback
      log.msg('caught: %s' % traceback.format_exc(e))

  def connectionLost(self, reason):
    if not isinstance(reason, client.ResponseDone):
      if reason.check(http.PotentialDataLoss):
        # Since the server is an HTTP 1.0 server, we always ignore
        # http.PotentialDataLoss
        pass
      else:
        # TODO: make this a state change
        log.msg('failure: %s' % reason)


class StatemachToggle(object):
  def __init__(self, statemach):
    self.statemach = statemach

  def __call__(self, doorOpen):
    if doorOpen:
      self.statemach.door_opened()
    else:
      self.statemach.door_closed()
