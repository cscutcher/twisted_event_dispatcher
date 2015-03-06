# -*- coding: utf-8 -*-
"""
Tests for twisted_event_dispatcher module
"""
import logging
import mock

from twisted.trial import unittest
from twisted.internet import defer

from twisted_event_dispatcher import EventDispatcher

DEV_LOGGER = logging.getLogger(__name__)


class TestEventDispatcher(unittest.TestCase):
    '''
    Test EventDispatcher
    '''
    factory = EventDispatcher

    @defer.inlineCallbacks
    def test_all_match(self):
        inst = self.factory(('username', 'role'))
        listen_fn = mock.Mock()

        yield inst.add_listener(listen_fn, 'during', username='bob', role='admin')
        event = 'some_event'

        yield inst.handle_event(event, username='bob', role='admin')

        listen_fn.assert_called_once_with(event)

    @defer.inlineCallbacks
    def test_no_match(self):
        inst = self.factory(('username', 'role'))
        listen_fn = mock.Mock()

        yield inst.add_listener(listen_fn, 'during', username='bob', role='admin')
        event = 'some_event'

        yield inst.handle_event(event, username='susan', role='admin')

        self.assertFalse(listen_fn.called, 'function should not have been called')

    @defer.inlineCallbacks
    def test_partial_match(self):
        inst = self.factory(('username', 'role'))
        listen_fn = mock.Mock()

        yield inst.add_listener(listen_fn, 'during', role='admin')
        event = 'some_event'

        yield inst.handle_event(event, username='susan', role='admin')

        listen_fn.assert_called_once_with(event)

    @defer.inlineCallbacks
    def test_remove(self):
        inst = self.factory(('username', 'role'))
        listen_fn = mock.Mock()

        handle = yield inst.add_listener(listen_fn, 'during', username='bob', role='admin')
        event = 'some_event'

        yield inst.handle_event(event, username='bob', role='admin')

        yield inst.remove_listener(handle)

        listen_fn.assert_called_once_with(event)

    @defer.inlineCallbacks
    def test_auto_remove(self):
        inst = self.factory(('username', 'role'))
        listen_fn = mock.Mock()

        # Create lambda that can be deleted
        def listen_fn_wrapper(event):
            return listen_fn(event)

        yield inst.add_listener(listen_fn_wrapper, 'during', username='bob', role='admin')
        del listen_fn_wrapper

        event = 'some_event'
        yield inst.handle_event(event, username='bob', role='admin')

        self.assertFalse(listen_fn.called, 'function should not have been called')

    @defer.inlineCallbacks
    def test_stop(self):
        inst = self.factory(('username', 'role'))
        listen_fn = mock.Mock()

        inst.add_listener(listen_fn, 'during', role='admin')
        event = 'some_event'
        inst.handle_event(event, username='susan', role='admin')

        yield inst.stop()

        listen_fn.assert_called_once_with(event)

        inst.handle_event(event, username='susan', role='admin')

        listen_fn.assert_called_once_with(event)

        inst.start()

        yield inst.handle_event(event, username='susan', role='admin')

        self.assertEqual(listen_fn.call_count, 2)
