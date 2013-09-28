#!/usr/bin/twistd -ny
# Monkey test of the state machine. Simulates random things happening at
# various intervals.

from twisted.application import internet
from twisted.application import service
from twisted.python import log
from doorcontrol import maestro
from state import statemach
import fake_chatcontrol
import fake_doorcontrol
import fake_doorsensor
import fake_presence

application = service.Application("statemach_regtest")

fake_broadcaster = fake_chatcontrol.FakeChatBroadcastProtocol()
door_controller = maestro.DoorControl(fake_doorcontrol.FakePololuMicroMaestro())

def fakeOsSystem(command):
  log.msg('os.system("%s")' % command)

# All times should be relative primes.
statemach = statemach.StateMachine(fake_broadcaster, door_controller,
    doorOpenTimeoutSecs=2, alertTimeoutSecs=1, system=fakeOsSystem)

fake_presence_service = internet.TimerService(
    3, fake_presence.randomPresence, statemach)
fake_presence_service.setServiceParent(application)

fake_doorsensor_service = internet.TimerService(
    5, fake_doorsensor.randomDoorState, statemach)
fake_doorsensor_service.setServiceParent(application)

commander = fake_chatcontrol.FakeChatCommandReceiverProtocol(statemach)
fake_xmpp_service = internet.TimerService(
    7, commander.pretendSomethingHappened)
fake_xmpp_service.setServiceParent(application)
