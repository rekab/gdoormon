import re

from twisted.internet import reactor
from twisted.internet import protocol
from twisted.internet import protocol

from twisted.words.xish import domish
from wokkel import xmppim
from wokkel import subprotocols


class SendMessageMixin:
  def sendMessage(self, body, to): 
    msg = domish.Element((None, 'message'))
    msg['to'] = to
    msg['type'] = 'chat'
    msg.addElement('body', content=body)
    self.send(msg)


class ChatBroadcastProtocol(SendMessageMixin, xmppim.XMPPHandler):
  def __init__(self, subscribers):
    self.subscribers = subscribers

  def sendAllSubscribers(self, text):
    for subscriber in self.subscribers:
      self.sendMessage(text, subscriber)


class ChatCommandReceiverProtocol(SendMessageMixin, xmppim.MessageProtocol):
  command_re = re.compile(r'(?P<command>\w+)\s*(?P<args>.*)')

  def __init__(self, statemach, subscribers):
    self.statemach = statemach
    self.subscribers = subscribers

  def connectionMade(self):
    # send initial presence
    self.send(xmppim.AvailablePresence())

  def onMessage(self, msg):
    if not (msg["type"] == 'chat' and hasattr(msg, "body") and msg.body):
      return
    command_match = self.command_re.match(str(msg.body))
    if command_match:
      result = self.dispatchCommand(
          msg["from"], command_match.group(1),
          re.split('\s+', command_match.group(2)))
    else:
      result = 'what?'
    self.sendMessage(result, msg["from"]) 

  def dispatchCommand(self, sender, cmd_str, cmd_args):
    event_name = 'command_%s' % cmd_str.lower()
    if hasattr(self, event_name):
      return getattr(self, event_name)(sender, cmd_args)
    if self.statemach.can(event_name):
      return getattr(self.statemach, event_name)(sender, cmd_args)
    return "bad command"

  def command_subscribe(self, sender, cmd_args):
    self.subscribers.add(sender)
    return '%s subscribed' % sender

  def command_unsubscribe(self, sender, cmd_args):
    if sender in self.subscribers:
      self.subscribers.remove(sender)
      return '%s unsubscribed' % sender
    return '%s not subscribed' % sender

  def command_snooze(self, sender, cmd_args):
    duration = None
    if not cmd_args:
      return 'need a duration'
    try:
      duration = int(cmd_args[0])
    except ValueError, e:
      return 'cannot parse "%s"' % cmd_args[0]
    return self.statemach.snoozeTimeout(int(cmd_args))

  def command_help(self, sender, cmd_args):
    return "help yourself"
