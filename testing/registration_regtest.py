#!/usr/bin/twistd -ny
from presence import registration
from twisted.application import internet
from twisted.application import service
from twisted.web import server

application = service.Application("registration_regtest")
sc = service.IServiceCollection(application)  # is this a cast?
#clients = clientdb.GetClientDb() # TODO
factory = server.Site(registration.GetRegistrationResource())
i = internet.TCPServer(8080, factory)
i.setServiceParent(sc)
