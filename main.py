#!/usr/bin/twistd -ny
import os
import sys
sys.path.append('.')

from chatcontrol import xmpp
from doorcontrol import maestro
from doorsensor import arduino_client
from presence import airport_clientmonitor
from presence import clientdb
from presence import registration
from state import statemach

from twisted.application import internet
from twisted.application import service
from twisted.persisted import dirdbm
from twisted.python import log
from twisted.python import logfile
from twisted.web import server
from twisted.words.protocols.jabber import jid
from twisted.words.xish import domish
from wokkel import client
import ConfigParser

# Constants.
APP_NAME = "gdoormon"
CONFIG_FNAME = 'gdoormon.config'

homedir = os.getenv('HOME')

# Setup logging
log.startLogging(
    logfile.LogFile.fromFullPath(
        './' + APP_NAME + '.log', maxRotatedFiles=20),
    setStdout=os.isatty(sys.stdout.fileno()))

# Load the config.
# TODO: file paths should be specified by a flag.
subscriber_dir = os.path.join(homedir, APP_NAME + '-subscribers')
config_path = os.path.join(os.getcwd(), CONFIG_FNAME)
if not os.path.exists(config_path):
  raise RuntimeError("Couldn't find %s" % config_path)
config = ConfigParser.ConfigParser()
config.read([config_path])


# Setup the application.
application = service.Application(APP_NAME)
sc = service.MultiService()
sc.setServiceParent(application)

# Start the client registration server.
factory = server.Site(registration.GetRegistrationResource())
server_port = int(config.get(APP_NAME, 'server_port'))
registration_server = internet.TCPServer(server_port, factory)
registration_server.setServiceParent(sc)

# Setup the XMPP service.
xmpp_user = config.get(APP_NAME, 'xmpp_user')
xmpp_passwd = config.get(APP_NAME, 'xmpp_passwd')
xmppclient = client.XMPPClient(
    jid.internJID('%s/%s' % (xmpp_user, APP_NAME)), xmpp_passwd)
xmppclient.logTraffic = True
xmppclient.setServiceParent(sc)

subscribers = dirdbm.DirDBM(subscriber_dir)
broadcaster = xmpp.ChatBroadcastProtocol(subscribers)
broadcaster.setHandlerParent(xmppclient)

# Setup the state machine and pass it the door controller and xmpp service.
door_controller = maestro.DoorControl(maestro.PololuMicroMaestro())
door_open_timeout_secs = int(config.get(APP_NAME, 'door_open_timeout_secs'))
alert_timeout_secs = int(config.get(APP_NAME, 'alert_timeout_secs'))
sm = statemach.StateMachine(broadcaster, door_controller,
    doorOpenTimeoutSecs=door_open_timeout_secs,
    alertTimeoutSecs=alert_timeout_secs)
commander = xmpp.ChatCommandReceiverProtocol(sm, subscribers)
commander.setHandlerParent(xmppclient)

# Setup a service to poll the airport, and pass it the state machine.
airport_hostname = config.get(APP_NAME, 'airport_hostname')
airport_polling_secs = int(config.get(APP_NAME, 'airport_polling_secs'))
clients = clientdb.getDb()
presence_toggle = airport_clientmonitor.StatemachToggle(sm)
monitor = airport_clientmonitor.PresenceMonitor(
    airport_hostname, clients, presence_toggle)
presence_service = internet.TimerService(airport_polling_secs, monitor.check)
presence_service.setServiceParent(sc)

# Setup a service to poll the door sensor, and pass it the state machine.
arduino_polling_secs = int(config.get(APP_NAME, 'arduino_polling_secs'))
arduino_hostname = config.get(APP_NAME, 'arduino_hostname')
threshold_cm = int(config.get(APP_NAME, 'arduino_threshold_cm'))
toggle = arduino_client.StatemachToggle(sm)
sensor = arduino_client.DoorSensor(toggle, hostname=arduino_hostname,
    threshold=threshold_cm)
sensor_service = internet.TimerService(arduino_polling_secs, sensor.check)
sensor_service.setServiceParent(sc)
