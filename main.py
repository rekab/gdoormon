#!/usr/bin/twistd -ny
import sys
sys.path.append('.') # todo: parse argv[0]

from presence import registration
from twisted.application import internet
from twisted.application import service
from twisted.application.internet import TimerService
from twisted.web import server
from twisted.words.xish import domish
from wokkel import xmppim


application = service.Application("gdoormon")
#sc = service.MultiService()
sc = service.IServiceCollection(application)  # is this a cast?

factory = server.Site(registration.GetRegistrationResource())
i = internet.TCPServer(8080, factory)
i.setServiceParent(sc)

xmppclient = XMPPClient(jid.internJID('%s/%s' % (USER, APP_NAME)), PASSWD)
xmppclient.logTraffic = True

subscribers = set() # TODO: dirdbm
broadcaster = chatcontrol.ChatBroadcastProtocol(subscribers)
broadcaster.setHandlerParent(xmppclient)

statemach = state.something(broadcast)
commander = chatcontrol.ChatCommandReceiverProtocol(statemach, subscribers)
commander.setHandlerParent(xmppclient)

xmppclient.setServiceParent(sc)

#pressence_service = TimerService(15, presence_process.PresenceDetector, statemach)
#presence_service.setServiceParent(sc)
#door_sensor = TimerService(15, door_sensor.DoorSensor, statemach)
#door_sensor.setServiceParent(sc)
