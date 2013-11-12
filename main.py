#!/usr/bin/twistd -ny
import sys
sys.path.append('.') # todo: parse argv[0]

from door_control import maestro
from presence import airport_clientmonitor
from presence import clientdb
from presence import registration
from state import statemach
from xmpp import chatcontrol

from twisted.application import internet
from twisted.application import service
from twisted.web import server
from twisted.words.xish import domish
from wokkel import client


application = service.Application("gdoormon")
#sc = service.MultiService()
sc = service.IServiceCollection(application)  # is this a cast?

clients = clientdb.getDb()
factory = server.Site(registration.GetRegistrationResource(clients))
i = internet.TCPServer(8080, factory)
i.setServiceParent(sc)

# TODO: config
xmppclient = client.XMPPClient(jid.internJID('%s/%s' % (USER, APP_NAME)), PASSWD)
xmppclient.logTraffic = True

subscribers = set() # TODO: dirdbm
broadcaster = chatcontrol.ChatBroadcastProtocol(subscribers)
broadcaster.setHandlerParent(xmppclient)

door_controller = maestro.DoorController()
statemach = statemach.StateMachine(broadcaster, door_controller)
commander = chatcontrol.ChatCommandReceiverProtocol(statemach, subscribers)
commander.setHandlerParent(xmppclient)

xmppclient.setServiceParent(sc)

airport_hostname = "hoth" # TODO: config
presence_toggle = airport_clientmonitor.StatemachToggle(statemach)
monitor = airport_clientmonitor.PresenceMonitor(
    airport_hostname, clients, presence_toggle)
pressence_service = internet.TimerService(15, monitor.check)
presence_service.setServiceParent(sc)

ds = internet.TimerService(15, doorsensor.DoorSensor, statemach)
sensor = arduino_client.DoorSensor() # TODO: config
sensor_service = internet.TimerService(15, sensor.check)
ds.setServiceParent(sc)
