#!/usr/bin/python

from presence import registration
from twisted.application import internet
from twisted.application import service
from twisted.application.internet import TimerService
from twisted.web import server


application = service.Application("gdoormon")
sc = service.IServiceCollection(application)

factory = server.Site(registration.GetRegistrationResource())
i = internet.TCPServer(8080, factory)
i.setServiceParent(sc)

#ts = TimerService(15, presence_process.)
#ts.setServiceParent(application? sc?)
