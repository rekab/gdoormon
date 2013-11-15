#!/usr/bin/twistd -ny
import os
import sys
sys.path.append('.') # todo: parse argv[0]

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
from twisted.web import server
from twisted.words.protocols.jabber import jid
from twisted.words.xish import domish
from wokkel import client
import ConfigParser

APP_NAME = "gdoormon"

# TODO: all these values should come from a standalone config file, the path
# should be specified by a flag.
SUBSCRIBER_DIR = os.path.join(os.getenv('HOME'), APP_NAME + '-subscribers')
CONFIG_FNAME = 'gdoormon.config'
config_path = os.path.join(os.getcwd(), CONFIG_FNAME)
if not os.path.exists(config_path):
  raise RuntimeError("Couldn't find %s" % config_path)
config = ConfigParser.ConfigParser()
config.read([config_path])


#AIRPORT_HOSTNAME = "hoth"
#XMPP_USER = os.environ.get('XMPP_USER', 'airvision@hindenburg.org')
#if 'XMPP_PASSWD' not in os.environ:
#  raise RuntimeError('set the $XMPP_PASSWD environment variable')
#XMPP_PASSWD = os.environ['XMPP_PASSWD']
#DOOR_OPEN_TIMEOUT_SECS=5
#ALERT_TIMEOUT_SECS=5
#AIRPORT_POLLING_SECS=15
#ARDUINO_POLLING_SECS=5

application = service.Application(APP_NAME)
sc = service.MultiService()
sc.setServiceParent(application)

# Start the client registration server.
factory = server.Site(registration.GetRegistrationResource())
server_port = int(config.get(APP_NAME, 'server_port'))
i = internet.TCPServer(server_port, factory)
i.setServiceParent(sc)

# Start the XMPP service.
xmpp_user = config.get(APP_NAME, 'xmpp_user')
xmpp_passwd = config.get(APP_NAME, 'xmpp_passwd')
xmppclient = client.XMPPClient(
    jid.internJID('%s/%s' % (xmpp_user, APP_NAME)), xmpp_passwd)
xmppclient.logTraffic = True

subscribers = dirdbm.DirDBM(SUBSCRIBER_DIR)
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

xmppclient.setServiceParent(sc)

# Setup a service to poll the airport.
airport_hostname = config.get(APP_NAME, 'airport_hostname')
airport_polling_secs = int(config.get(APP_NAME, 'airport_polling_secs'))
clients = clientdb.getDb()
presence_toggle = airport_clientmonitor.StatemachToggle(sm)
monitor = airport_clientmonitor.PresenceMonitor(
    airport_hostname, clients, presence_toggle)
presence_service = internet.TimerService(airport_polling_secs, monitor.check)
presence_service.setServiceParent(sc)

# Setup a service to poll the door sensor.
arduino_polling_secs = int(config.get(APP_NAME, 'arduino_polling_secs'))
arduino_hostname = config.get(APP_NAME, 'arduino_hostname')
threshold_cm = int(config.get(APP_NAME, 'arduino_threshold_cm'))
toggle = arduino_client.StatemachToggle(sm)
sensor = arduino_client.DoorSensor(toggle, hostname=arduino_hostname,
    threshold=threshold_cm)
sensor_service = internet.TimerService(arduino_polling_secs, sensor.check)
sensor_service.setServiceParent(sc)
