from doorcontrol import maestro
from doorsensor import arduino_client
from state import statemach

from twisted.application import internet
from twisted.application import service
from testing import fake_chatcontrol
from testing import fake_doorcontrol
from twisted.python import log

def fakeOsSystem(command):
  log.msg('os.system("%s")' % command)


application = service.Application("arduino_client_regtest")

fake_broadcaster = fake_chatcontrol.FakeChatBroadcastProtocol()
door_controller = maestro.DoorControl(fake_doorcontrol.FakePololuMicroMaestro())
sm = statemach.StateMachine(fake_broadcaster, door_controller,
    doorOpenTimeoutSecs=2.1, alertTimeoutSecs=1.3, system=fakeOsSystem)

toggle = arduino_client.StatemachToggle(sm)
sensor = arduino_client.DoorSensor(toggle)

sensor_service = internet.TimerService(3, sensor.check)
sensor_service.setServiceParent(application)
