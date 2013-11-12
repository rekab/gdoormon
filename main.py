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
from twisted.web import server
from twisted.words.protocols.jabber import jid
from twisted.words.xish import domish
from wokkel import client


APP_NAME = "gdoormon"
application = service.Application(APP_NAME)
#sc = service.MultiService()
sc = service.IServiceCollection(application)  # is this a cast?

# Start the client registration server.
factory = server.Site(registration.GetRegistrationResource())
i = internet.TCPServer(8080, factory)
i.setServiceParent(sc)


# Start the XMPP service.
# TODO: config
USER = os.environ.get('XMPP_USER', 'airvision@hindenburg.org')
if 'XMPP_PASSWD' not in os.environ:
  raise RuntimeError('set the $XMPP_PASSWD environment variable')

PASSWD = os.environ['XMPP_PASSWD']
xmppclient = client.XMPPClient(jid.internJID('%s/%s' % (USER, APP_NAME)), PASSWD)
xmppclient.logTraffic = True

subscribers = set() # TODO: dirdbm
broadcaster = xmpp.ChatBroadcastProtocol(subscribers)
broadcaster.setHandlerParent(xmppclient)

# Setup the state machine and pass it the door controller and xmpp service.
door_controller = maestro.DoorControl(maestro.PololuMicroMaestro())
statemach = statemach.StateMachine(broadcaster, door_controller, #)
    doorOpenTimeoutSecs=2.1, alertTimeoutSecs=1.3)
commander = xmpp.ChatCommandReceiverProtocol(statemach, subscribers)
commander.setHandlerParent(xmppclient)

xmppclient.setServiceParent(sc)

# Setup a service to poll the airport.
airport_hostname = "hoth" # TODO: config
clients = clientdb.getDb()
presence_toggle = airport_clientmonitor.StatemachToggle(statemach)
monitor = airport_clientmonitor.PresenceMonitor(
    airport_hostname, clients, presence_toggle)
presence_service = internet.TimerService(15, monitor.check)
presence_service.setServiceParent(sc)

# Setup a service to poll the door sensor.
toggle = arduino_client.StatemachToggle(statemach)
sensor = arduino_client.DoorSensor(toggle) # TODO: config
sensor_service = internet.TimerService(5, sensor.check)
sensor_service.setServiceParent(sc)
