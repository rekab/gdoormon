#!/usr/bin/twistd -ny
from doorcontrol import maestro
from twisted.application import internet
from twisted.application import service

application = service.Application("registration_regtest")

control = maestro.DoorControl(maestro.PololuMicroMaestro())
button_masher = internet.TimerService(5, control.hitButton)
button_masher.setServiceParent(application)
