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

    def setUp(self):
        self.inst = self.factory(('username', 'role'))

    def tearDown(self):
        return self.inst.stop()

    @defer.inlineCallbacks
    def test_all_match(self):
        '''
        Test event handler is fired when all details match
        '''
        listen_fn = mock.Mock()

        yield self.inst.add_event_handler(listen_fn, 'during', username='bob', role='admin')
        event = 'some_event'

        yield self.inst.handle_event(event, username='bob', role='admin')

        listen_fn.assert_called_once_with(event)

    @defer.inlineCallbacks
    def test_no_match(self):
        '''
        Test handler doesn't fire when no details match
        '''
        listen_fn = mock.Mock()

        yield self.inst.add_event_handler(listen_fn, 'during', username='bob', role='admin')
        event = 'some_event'

        yield self.inst.handle_event(event, username='susan', role='admin')

        self.assertFalse(listen_fn.called, 'function should not have been called')

    @defer.inlineCallbacks
    def test_partial_match(self):
        '''
        Test handler fires when one detail matches, and remaining details are unspecifed
        '''
        listen_fn = mock.Mock()

        yield self.inst.add_event_handler(listen_fn, 'during', role='admin')
        event = 'some_event'

        yield self.inst.handle_event(event, username='susan', role='admin')

        listen_fn.assert_called_once_with(event)

    @defer.inlineCallbacks
    def test_remove(self):
        '''
        Test a removed handler no longer fires
        '''
        listen_fn = mock.Mock()

        handle = yield self.inst.add_event_handler(
            listen_fn, 'during', username='bob', role='admin')
        event = 'some_event'

        yield self.inst.handle_event(event, username='bob', role='admin')

        yield self.inst.remove_event_handler(handle)

        listen_fn.assert_called_once_with(event)

    @defer.inlineCallbacks
    def test_auto_remove(self):
        '''
        Test that a function that is garbage collected no longer fires indicating it has
        been automatically removed from dispatcher
        '''
        listen_fn = mock.Mock()

        # Create lambda that can be deleted
        def listen_fn_wrapper(event):
            return listen_fn(event)

        yield self.inst.add_event_handler(
            listen_fn_wrapper, 'during', username='bob', role='admin')
        del listen_fn_wrapper

        event = 'some_event'
        yield self.inst.handle_event(event, username='bob', role='admin')

        self.assertFalse(listen_fn.called, 'function should not have been called')

    @defer.inlineCallbacks
    def test_stop_start(self):
        '''
        Test that stopping and starting dispatcher prevent and allow handling as expected.
        '''
        listen_fn = mock.Mock()

        self.inst.add_event_handler(listen_fn, 'during', role='admin')
        event = 'some_event'
        self.inst.handle_event(event, username='susan', role='admin')

        yield self.inst.stop()

        listen_fn.assert_called_once_with(event)

        self.inst.handle_event(event, username='susan', role='admin')

        listen_fn.assert_called_once_with(event)

        self.inst.start()

        yield self.inst.handle_event(event, username='susan', role='admin')

        self.assertEqual(listen_fn.call_count, 2)

    def test_invalid_spec(self):
        '''
        Test that specify a match spec that isn't present during setup raises an exception.
        '''
        listen_fn = mock.Mock()

        self.assertRaises(
            ValueError,
            self.inst.add_event_handler,
            listen_fn,
            'during',
            password='admin')
