#!/usr/bin/twistd -ny
# Monkey test of the state machine. Simulates random things happening at
# various intervals.

from twisted.application import internet
from twisted.application import service
from twisted.python import log
from doorcontrol import maestro
from state import statemach
from testing import fake_chatcontrol
from testing import fake_doorcontrol
from testing import fake_doorsensor
from testing import fake_presence

application = service.Application("statemach_regtest")

fake_broadcaster = fake_chatcontrol.FakeChatBroadcastProtocol()
door_controller = maestro.DoorControl(fake_doorcontrol.FakePololuMicroMaestro())

def fakeOsSystem(command):
  log.msg('os.system("%s")' % command)

# All times should be relative primes.
sm = statemach.StateMachine(fake_broadcaster, door_controller,
    doorOpenTimeoutSecs=2.1, alertTimeoutSecs=1.3, system=fakeOsSystem)

fake_presence_service = internet.TimerService(
    3.55, fake_presence.randomPresence, sm)
fake_presence_service.setServiceParent(application)

fake_doorsensor_service = internet.TimerService(
    5.7, fake_doorsensor.randomDoorState, sm)
fake_doorsensor_service.setServiceParent(application)

commander = fake_chatcontrol.FakeChatCommandReceiverProtocol(sm)
fake_xmpp_service = internet.TimerService(
    7, commander.pretendSomethingHappened)
fake_xmpp_service.setServiceParent(application)
