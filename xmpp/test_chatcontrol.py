#!/usr/bin/trial

from twisted.trial import unittest
from twisted.words.xish import domish
from xmpp import chatcontrol


class FakeStatemach(object):
  def __init__(self, valid_commands):
    self.valid_commands = valid_commands
    self.called = []

  def can(self, command):
    return command in self.valid_commands

  def __getattr__(self, attr):
    """Return a lambda that records the call to the statemach."""
    return lambda sender, args: self.recordCall(attr, sender, args)

  def recordCall(self, attr, sender, args):
    self.called.append((attr, sender, args))
    return 'ok'


class TestChatProtocolBase(unittest.TestCase):
  def setUp(self):
    self.sent = []
    self.subscribers = set(['a', 'b', 'c'])

  def mockSend(self, msg):
    self.sent.append(msg)


class TestBroadcastProtocol(TestChatProtocolBase):
  def setUp(self):
    TestChatProtocolBase.setUp(self)
    self.broadcast = chatcontrol.ChatBroadcastProtocol(self.subscribers)
    self.patch(self.broadcast, 'send', self.mockSend)

  def testSendAllSubscribers(self):
    self.broadcast.sendAllSubscribers('hello')
    self.assertNotEquals(len(self.subscribers), 0)
    for sent in self.sent:
      self.subscribers.remove(sent['to'])
    self.assertEquals(len(self.subscribers), 0)


class ChatCommandReceiverProtocol(TestChatProtocolBase):
  def setUp(self):
    TestChatProtocolBase.setUp(self)
    self.statemach = FakeStatemach(set(['command_test_command']))
    self.receiver = chatcontrol.ChatCommandReceiverProtocol(
        self.statemach, self.subscribers)
    self.patch(self.receiver, 'send', self.mockSend)

  def receiveFakeMessage(self, text, sender):
    msg = domish.Element((None, 'message'))
    msg['from'] = sender
    msg['type'] = 'chat'
    msg.addElement('body', content=text)
    self.receiver.onMessage(msg)

  def testHelp(self):
    self.receiveFakeMessage('help me!', 'foo')
    self.assertEquals(1, len(self.sent))
    self.assertEquals('help yourself', str(self.sent[0].body))
    # Verify the statemach wasn't touched
    self.assertEquals(0, len(self.statemach.called))

  def testSubscribe(self):
    # unsubscribe
    self.receiveFakeMessage('unsubscribe', 'so-and-so')
    self.assertEquals('so-and-so not subscribed', str(self.sent.pop().body))
    self.assertTrue('so-and-so' not in self.subscribers)

    # subscribe
    self.receiveFakeMessage('subscribe', 'so-and-so')
    self.assertEquals('so-and-so subscribed', str(self.sent.pop().body))
    self.assertTrue('so-and-so' in self.subscribers)

    # unsubscribe
    self.receiveFakeMessage('unsubscribe', 'so-and-so')
    self.assertEquals('so-and-so unsubscribed', str(self.sent.pop().body))
    self.assertTrue('so-and-so' not in self.subscribers)
    self.assertEquals(0, len(self.sent))

    # Verify the statemach wasn't touched
    self.assertEquals(0, len(self.statemach.called))

  def testStateMachCall(self):
    self.assertEquals(0, len(self.statemach.called))
    self.receiveFakeMessage('test_command with args', 'foo')
    self.assertEquals(
        ('command_test_command', 'foo', ['with', 'args']),
        self.statemach.called.pop())
    self.assertEquals(0, len(self.statemach.called))

  def testInvalidCommand(self):
    self.receiveFakeMessage('hey are you there?', 'foo')
    self.assertEquals(0, len(self.statemach.called))
    self.assertEquals('so-and-so unsubscribed', str(self.sent.pop().body))
    self.assertTrue('so-and-so' not in self.subscribers)
    self.assertEquals(0, len(self.sent))

  def testStateMachCall(self):
    self.assertEquals(0, len(self.statemach.called))
    self.receiveFakeMessage('test_command with args', 'foo')
    self.assertEquals(
        ('command_test_command', 'foo', ['with', 'args']),
        self.statemach.called.pop())
    self.assertEquals(0, len(self.statemach.called))

  def testInvalidCommand(self):
    self.receiveFakeMessage('hey are you there?', 'foo')
    self.assertEquals(0, len(self.statemach.called))
    self.assertEquals('bad command', str(self.sent.pop().body))
    self.assertEquals(0, len(self.sent))
