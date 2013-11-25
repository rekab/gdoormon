import re

from twisted.internet import protocol
from twisted.internet import protocol
from twisted.python import log

from twisted.words.xish import domish
from wokkel import xmppim
from wokkel import subprotocols


# How long alert snooze lasts (in seconds).
DEFAULT_SNOOZE_DURATION = 20


class SendMessageMixin:
  def sendMessage(self, body, to): 
    msg = domish.Element((None, 'message'))
    msg['to'] = to
    msg['type'] = 'chat'
    msg.addElement('body', content=body)
    self.send(msg)

def requiresAuthentication(func):
  """Authorization decorator."""
  def checkAuth(self, user, cmd_args):
    if not self.isSubscriber(user):
      msg = '%s is not subscribed' % user
      log.msg(msg)
      return msg
    return func(self, user, cmd_args)
  return checkAuth


class ChatBroadcastProtocol(SendMessageMixin, xmppim.XMPPHandler):
  def __init__(self, subscribers):
    self.subscribers = subscribers

  def sendAllSubscribers(self, text):
    log.msg('broadcasting message to %d subscribers: %s' %
        (len(self.subscribers), text))
    for subscriber in self.subscribers.keys():
      self.sendMessage(text, subscriber)


class ChatCommandReceiverProtocol(SendMessageMixin, xmppim.MessageProtocol):
  command_re = re.compile(r'(?P<command>\w+)\s*(?P<args>.*)')

  def __init__(self, statemach, subscribers, password):
    self.statemach = statemach
    self.subscribers = subscribers
    self.password = password

  def connectionMade(self):
    # send initial presence
    self.send(xmppim.AvailablePresence())

  def onMessage(self, msg):
    if not (msg["type"] == 'chat' and hasattr(msg, "body") and msg.body):
      return
    command_match = self.command_re.match(str(msg.body))
    if command_match:
      log.msg('dispatching command: %s' % msg.body)
      result = self.dispatchCommand(
          msg["from"], command_match.group(1),
          re.split('\s+', command_match.group(2)))
    else:
      log.msg('Got bogus message: %s' % msg.body)
      result = 'what?'
    self.sendMessage(result, msg["from"]) 

  def dispatchCommand(self, sender, cmd_str, cmd_args):
    event_name = 'command_%s' % cmd_str.lower()
    if hasattr(self, event_name):
      log.msg('Calling %s(%s, %s) on self' % (event_name, sender, cmd_args))
      return getattr(self, event_name)(sender, cmd_args)

    # XXX: duplicated message from requiresAuthentication
    if not self.isSubscriber(sender):
      msg = 'not subscribed; send subscribe <password>'
      log.msg(msg)
      return msg

    if self.statemach.can(event_name):
      log.msg('Calling %s(%s, %s) on statemach' % (
          event_name, sender, cmd_args))
      return getattr(self.statemach, event_name)(sender=sender, args=cmd_args)
    log.msg('Bad command %s' % event_name)
    return 'bad command'

  def command_subscribe(self, sender, cmd_args):
    passwd = cmd_args[0] if cmd_args else None
    if not passwd:
      log.msg('subscription request lacks password')
      return 'usage: subscribe <password>'
    if passwd != self.password:
      log.msg('subscription request has bad password')
      return 'bad password'
    self.subscribers[str(sender)] = ''
    msg = '%s subscribed' % sender
    log.msg(msg)
    return msg

  def isSubscriber(self, user):
    """Check if the user is subscribed.

    Args:
      user: xmpp user string
    Returns:
      boolean
    """
    # Note: have to use .keys() because dirdbm isn't a real dict
    return user in self.subscribers.keys()

  @requiresAuthentication
  def command_unsubscribe(self, sender, cmd_args):
    if sender in self.subscribers.keys():
      del self.subscribers[sender]
      msg = '%s unsubscribed' % sender
    else:
      msg = '%s not subscribed' % sender
    log.msg(msg)
    return msg

  @requiresAuthentication
  def command_snooze(self, sender, cmd_args):
    duration = None
    if not cmd_args or not cmd_args[0]:
      duration = DEFAULT_SNOOZE_DURATION

    try:
      duration = int(cmd_args[0])
    except ValueError, e:
      return 'cannot parse "%s"' % cmd_args[0]
    log.msg('calling statemach.snoozeAlert(%d)' % duration)
    return self.statemach.snoozeAlert(duration)

  def command_help(self, sender, cmd_args):
    return "help yourself"
