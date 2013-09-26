#!/usr/bin/twistd -ny
import os
from presence import registration
from twisted.application import internet
from twisted.application import service
from twisted.words.protocols.jabber import jid
from wokkel import client
from xmpp import chatcontrol
from xmpp import test_chatcontrol

# TODO: config file
USER = os.environ.get('XMPP_USER', 'airvision@hindenburg.org')
if 'XMPP_PASSWD' not in os.environ:
  raise RuntimeError('set the $XMPP_PASSWD environment variable')

PASSWD = os.environ['XMPP_PASSWD']

app_name = "chatcontrol_regtest"
application = service.Application(app_name)
sc = service.MultiService()
sc.setServiceParent(application)

xmppclient = client.XMPPClient(jid.internJID('%s/%s' % (USER, app_name)), PASSWD)
xmppclient.logTraffic = True
xmppclient.setServiceParent(sc)

subscribers = set() # TODO: dirdbm
broadcaster = chatcontrol.ChatBroadcastProtocol(subscribers)
broadcaster.setHandlerParent(xmppclient)

statemach = test_chatcontrol.FakeStatemach([])
commander = chatcontrol.ChatCommandReceiverProtocol(statemach, subscribers)
commander.setHandlerParent(xmppclient)
