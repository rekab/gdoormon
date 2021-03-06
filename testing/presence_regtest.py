from doorcontrol import maestro
from presence import airport_clientmonitor
from presence import clientdb
from state import statemach
from testing import fake_chatcontrol
from testing import fake_doorcontrol
from twisted.application import internet
from twisted.application import service
from twisted.python import log


def fakeOsSystem(command):
  log.msg('os.system("%s")' % command)


application = service.Application("gdoormon")

fake_broadcaster = fake_chatcontrol.FakeChatBroadcastProtocol()
door_controller = maestro.DoorControl(fake_doorcontrol.FakePololuMicroMaestro())
sm = statemach.StateMachine(fake_broadcaster, door_controller,
    doorOpenTimeoutSecs=2.1, alertTimeoutSecs=1.3, system=fakeOsSystem)

toggle = airport_clientmonitor.StatemachToggle(sm)
clients = clientdb.getDb()
# TODO: config
airport_hostname = "hoth"
monitor = airport_clientmonitor.PresenceMonitor(airport_hostname, clients, toggle)

presence_service = internet.TimerService(15, monitor.check)
presence_service.setServiceParent(application)
