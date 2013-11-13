#!/usr/bin/twistd -ny
import os
import sys
sys.path.append('.') # todo: parse argv[0]

from chatcontrol import xmpp
from doorcontrol import maestro
from doorsensor import arduino_client
from presence import airport_clientmonitor
from presence import clientdb
from presence import registration
from state import statemach

from twisted.application import internet
from twisted.application import service
from twisted.persisted import dirdbm
from twisted.web import server
from twisted.words.protocols.jabber import jid
from twisted.words.xish import domish
from wokkel import client


# TODO: all these values should come from a standalone config file, the path
# should be specified by a flag.
APP_NAME = "gdoormon"
AIRPORT_HOSTNAME = "hoth"
SUBSCRIBER_DIR = os.path.join(os.getenv('HOME'), APP_NAME + '-subscribers')
XMPP_USER = os.environ.get('XMPP_USER', 'airvision@hindenburg.org')
if 'XMPP_PASSWD' not in os.environ:
  raise RuntimeError('set the $XMPP_PASSWD environment variable')
XMPP_PASSWD = os.environ['XMPP_PASSWD']
DOOR_OPEN_TIMEOUT_SECS=5
ALERT_TIMEOUT_SECS=5
AIRPORT_POLLING_SECS=15
ARDUINO_POLLING_SECS=5


application = service.Application(APP_NAME)
sc = service.IServiceCollection(application)

# Start the client registration server.
factory = server.Site(registration.GetRegistrationResource())
i = internet.TCPServer(8080, factory)
i.setServiceParent(sc)

# Start the XMPP service.
xmppclient = client.XMPPClient(
    jid.internJID('%s/%s' % (XMPP_USER, APP_NAME)), XMPP_PASSWD)
xmppclient.logTraffic = True

subscribers = dirdbm.DirDBM(SUBSCRIBER_DIR)
broadcaster = xmpp.ChatBroadcastProtocol(subscribers)
broadcaster.setHandlerParent(xmppclient)

# Setup the state machine and pass it the door controller and xmpp service.
door_controller = maestro.DoorControl(maestro.PololuMicroMaestro())
statemach = statemach.StateMachine(broadcaster, door_controller,
    doorOpenTimeoutSecs=DOOR_OPEN_TIMEOUT_SECS,
    alertTimeoutSecs=ALERT_TIMEOUT_SECS)
commander = xmpp.ChatCommandReceiverProtocol(statemach, subscribers)
commander.setHandlerParent(xmppclient)

xmppclient.setServiceParent(sc)

# Setup a service to poll the airport.
clients = clientdb.getDb()
presence_toggle = airport_clientmonitor.StatemachToggle(statemach)
monitor = airport_clientmonitor.PresenceMonitor(
    AIRPORT_HOSTNAME, clients, presence_toggle)
presence_service = internet.TimerService(AIRPORT_POLLING_SECS, monitor.check)
presence_service.setServiceParent(sc)

# Setup a service to poll the door sensor.
toggle = arduino_client.StatemachToggle(statemach)
sensor = arduino_client.DoorSensor(toggle) # TODO: config
sensor_service = internet.TimerService(ARDUINO_POLLING_SECS, sensor.check)
sensor_service.setServiceParent(sc)
