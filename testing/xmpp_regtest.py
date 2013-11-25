#!/usr/bin/twistd -ny
import os
from presence import registration
from twisted.application import internet
from twisted.application import service
from twisted.words.protocols.jabber import jid
from wokkel import client
from chatcontrol import xmpp
from chatcontrol import test_xmpp

if 'XMPP_USER' not in os.environ:
  raise RuntimeError('set the $XMPP_USER environment variable')
if 'XMPP_PASSWD' not in os.environ:
  raise RuntimeError('set the $XMPP_PASSWD environment variable')

USER = os.environ['XMPP_USER']
PASSWD = os.environ['XMPP_PASSWD']
GDOORMON_PASSWD = 'hunter2'

app_name = "chatcontrol_regtest"
application = service.Application(app_name)
sc = service.MultiService()
sc.setServiceParent(application)

xmppclient = client.XMPPClient(jid.internJID('%s/%s' % (USER, app_name)), PASSWD)
xmppclient.logTraffic = True
xmppclient.setServiceParent(sc)

subscribers = set() # TODO: dirdbm
broadcaster = xmpp.ChatBroadcastProtocol(subscribers)
broadcaster.setHandlerParent(xmppclient)

statemach = test_xmpp.FakeStatemach([])
commander = xmpp.ChatCommandReceiverProtocol(
    statemach, subscribers, GDOORMON_PASSWD)
commander.setHandlerParent(xmppclient)
