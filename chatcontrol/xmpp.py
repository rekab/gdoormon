import re

from twisted.python import log

from twisted.words.xish import domish
from wokkel import xmppim


# How long alert snooze lasts (in minutes).
DEFAULT_SNOOZE_DURATION = 5


class SendMessageMixin:
  def sendMessage(self, body, to): 
    msg = domish.Element((None, 'message'))
    msg['to'] = to
    msg['type'] = 'chat'
    msg.addElement('body', content=body)
    self.send(msg)

def requiresAuthorization(func):
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
      # Split the JID address from the resource.
      sender = msg["from"]
      jid_parts = sender.split('/', 2)
      if len(jid_parts) != 2:
        log.msg('malformed sender address: %s' % sender)
        return 'internal error'
      address = jid_parts[0]

      # Dispatch the command.
      log.msg('dispatching command from %s: %s' % (address, msg.body))
      result = self.dispatchCommand(
          address, command_match.group(1),
          re.split('\s+', command_match.group(2)))
    else:
      log.msg('Got bogus message: %s' % msg.body)
      result = 'what?'
    if result:
      log.msg('Replying: %s' % repr(result))
      self.sendMessage(result, msg["from"]) 
    else:
      log.msg('No reply to send.')

  def dispatchCommand(self, sender, cmd_str, cmd_args):
    event_name = 'command_%s' % cmd_str.lower()
    if hasattr(self, event_name):
      log.msg('Calling %s(%s, %s) on self' % (event_name, sender, cmd_args))
      return getattr(self, event_name)(sender, cmd_args)

    # XXX: duplicated message from requiresAuthorization
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

  @requiresAuthorization
  def command_unsubscribe(self, sender, cmd_args):
    del self.subscribers[str(sender)]
    msg = '%s unsubscribed' % sender
    log.msg(msg)
    return msg

  @requiresAuthorization
  def command_snooze(self, sender, cmd_args):
    duration = None
    if not cmd_args or not cmd_args[0]:
      duration = DEFAULT_SNOOZE_DURATION
    else:
      try:
        # Note that we use float(), which is handy for testing <1m intervals.
        duration = float(cmd_args[0])
      except ValueError:
        return 'cannot parse "%s"' % cmd_args[0]
    duration *= 60.0  # convert to minutes
    log.msg('calling statemach.snoozeAlert(%d)' % duration)
    return self.statemach.snoozeAlert(duration)

  @requiresAuthorization
  def command_status(self, sender, cmd_args):
    # TODO: timer stats, counts
    return self.statemach.getState()

  def command_help(self, sender, cmd_args):
    return "commands: help, status, snooze, snooze <minutes>, close_door"
