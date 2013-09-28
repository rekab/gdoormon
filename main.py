#!/usr/bin/twistd -ny
import sys
sys.path.append('.') # todo: parse argv[0]

from door_control import maestro
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

clients = clientdb.GetClientDb() # TODO
factory = server.Site(registration.GetRegistrationResource(clients))
i = internet.TCPServer(8080, factory)
i.setServiceParent(sc)

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

#pressence_service = internet.TimerService(15, presence_process.PresenceDetector, statemach, clients)
#presence_service.setServiceParent(sc)
#door_sensor = internet.TimerService(15, door_sensor.DoorSensor, statemach)
#door_sensor.setServiceParent(sc)
