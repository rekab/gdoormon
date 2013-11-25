#!/usr/bin/trial

from twisted.trial import unittest
from twisted.words.xish import domish
import xmpp


TEST_PASSWORD = 'hunter2'


class FakeStatemach(object):
  def __init__(self, valid_commands):
    self.valid_commands = valid_commands
    self.called = []

  def can(self, command):
    return command in self.valid_commands

  def __getattr__(self, attr):
    """Return a lambda that records the call to the statemach."""
    return lambda *args, **kw: self.recordCall(attr, *args, **kw)

  def recordCall(self, attr, *args, **kw):
    self.called.append((attr, args, kw))
    return 'ok'


class TestChatProtocolBase(unittest.TestCase):
  def setUp(self):
    self.sent = []
    self.subscribers = {'a': 1, 'b': 1, 'c': 1}

  def mockSend(self, msg):
    self.sent.append(msg)


class TestBroadcastProtocol(TestChatProtocolBase):
  def setUp(self):
    TestChatProtocolBase.setUp(self)
    self.broadcast = xmpp.ChatBroadcastProtocol(self.subscribers)
    self.patch(self.broadcast, 'send', self.mockSend)

  def testSendAllSubscribers(self):
    self.broadcast.sendAllSubscribers('hello')
    self.assertNotEquals(len(self.subscribers), 0)
    for sent in self.sent:
      del self.subscribers[sent['to']]
    self.assertEquals(len(self.subscribers), 0)


class ChatCommandReceiverProtocol(TestChatProtocolBase):
  def setUp(self):
    TestChatProtocolBase.setUp(self)
    self.statemach = FakeStatemach(set(['command_test_command']))
    self.receiver = xmpp.ChatCommandReceiverProtocol(
        self.statemach, self.subscribers, TEST_PASSWORD)
    self.patch(self.receiver, 'send', self.mockSend)

  def receiveFakeMessage(self, text, sender):
    msg = domish.Element((None, 'message'))
    msg['from'] = sender
    msg['type'] = 'chat'
    msg.addElement('body', content=text)
    self.receiver.onMessage(msg)

  def testHelp(self):
    self.receiveFakeMessage('help me!', 'foo@example.com/zzzz')
    self.assertEquals(1, len(self.sent))
    self.assertEquals('help yourself', str(self.sent[0].body))
    # Verify the statemach wasn't touched
    self.assertEquals(0, len(self.statemach.called))

  def testMalformedFromAddress(self):
    self.receiveFakeMessage('help me!', '~~~bogus~~~')
    self.assertEquals(0, len(self.sent))
    self.assertEquals(0, len(self.statemach.called))

  def testSubscribe(self):
    # unsubscribe
    self.receiveFakeMessage('unsubscribe', 'foo@example.com/asdf')
    self.assertEquals(
        'foo@example.com is not subscribed', str(self.sent.pop().body))
    self.assertTrue('foo' not in self.subscribers)

    # subscribe with missing password
    self.receiveFakeMessage('subscribe', 'foo@example.com/asdf')
    self.assertEquals('usage: subscribe <password>', str(self.sent.pop().body))
    self.assertFalse('foo' in self.subscribers)

    # subscribe with bad password
    self.receiveFakeMessage('subscribe asdf', 'foo@example.com/asdf')
    self.assertEquals('bad password', str(self.sent.pop().body))
    self.assertFalse('foo@example.com' in self.subscribers)

    # subscribe with good password
    self.receiveFakeMessage(
        'subscribe %s' % TEST_PASSWORD, 'foo@example.com/asdf')
    self.assertEquals('foo@example.com subscribed', str(self.sent.pop().body))
    self.assertTrue('foo@example.com' in self.subscribers)

    # unsubscribe (from a different resource)
    self.receiveFakeMessage('unsubscribe', 'foo@example.com/quux')
    self.assertEquals(
        'foo@example.com unsubscribed', str(self.sent.pop().body))
    self.assertTrue('foo@example.com' not in self.subscribers)
    self.assertEquals(0, len(self.sent))

    # unsubscribe: should be an error
    self.receiveFakeMessage('unsubscribe', 'foo@example.com/asdf')
    self.assertEquals(
        'foo@example.com is not subscribed', str(self.sent.pop().body))
    self.assertTrue('foo@example.com' not in self.subscribers)
    self.assertEquals(0, len(self.sent))

    # Verify the statemach wasn't touched
    self.assertEquals(0, len(self.statemach.called))

  def testStateMachCall(self):
    self.receiveFakeMessage(
        'subscribe %s' % TEST_PASSWORD, 'foo@example.com/asdf')
    self.assertEquals('foo@example.com subscribed', str(self.sent.pop().body))
    self.assertEquals(0, len(self.statemach.called))

    self.receiveFakeMessage('test_command with args', 'foo@example.com/asdf')
    self.assertEquals('ok', str(self.sent.pop().body))
    self.assertEquals(1, len(self.statemach.called))
    self.assertEquals(
        ('command_test_command',
          (),
          {'args': ['with', 'args'], 'sender': 'foo@example.com'}),
        self.statemach.called.pop())
    self.assertEquals(0, len(self.statemach.called))

  def testInvalidCommand(self):
    # test unsubscribed user
    self.receiveFakeMessage('hey are you there?', 'foo@example.com/asdf')
    self.assertEquals(0, len(self.statemach.called))
    self.assertEquals(
        'not subscribed; send subscribe <password>', str(self.sent.pop().body))
    self.assertEquals(0, len(self.sent))

    # subscribe with good password
    self.receiveFakeMessage(
        'subscribe %s' % TEST_PASSWORD, 'foo@example.com/zxcv')
    self.assertEquals('foo@example.com subscribed', str(self.sent.pop().body))

    # test bogus text
    self.receiveFakeMessage('hey are you there?', 'foo@example.com/asdf')
    self.assertEquals(0, len(self.statemach.called))
    self.assertEquals('bad command', str(self.sent.pop().body))
    self.assertEquals(0, len(self.sent))

  def testSnooze(self):
    # subscribe with bad password
    self.receiveFakeMessage('subscribe asdf', 'foo@example.com/asdf')
    self.assertEquals('bad password', str(self.sent.pop().body))
    self.assertFalse('foo@example.com' in self.subscribers)

    # attempt to snooze: should be ignored
    self.receiveFakeMessage('snooze 10', 'foo@example.com/asdf')
    self.assertEquals(
        'foo@example.com is not subscribed', str(self.sent.pop().body))
    self.assertEquals(0, len(self.statemach.called))

    # subscribe with good password
    self.receiveFakeMessage(
        'subscribe %s' % TEST_PASSWORD, 'foo@example.com/asdf')
    self.assertEquals('foo@example.com subscribed', str(self.sent.pop().body))
    self.assertTrue('foo@example.com' in self.subscribers)

    # snooze with bad number
    self.receiveFakeMessage('snooze plz', 'foo@example.com/zxcv')
    self.assertEquals('cannot parse "plz"', str(self.sent.pop().body))
    self.assertEquals(0, len(self.statemach.called))

    # valid snooze
    self.receiveFakeMessage('snooze 10', 'foo@example.com/zxcv')
    self.assertEquals('ok', str(self.sent.pop().body))
    self.assertEquals(1, len(self.statemach.called))

