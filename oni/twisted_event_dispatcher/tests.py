# -*- coding: utf-8 -*-
"""
Tests for twisted_event_dispatcher module
"""
import logging
import mock

from twisted.trial import unittest
from twisted.internet import defer

from oni.twisted_event_dispatcher import EventDispatcher

DEV_LOGGER = logging.getLogger(__name__)


class TestEventDispatcher(unittest.TestCase):
    '''
    Test EventDispatcher
    '''
    factory = EventDispatcher

    def setUp(self):
        '''setUp test'''
        self.inst = self.factory(('username', 'role'))
        self.inst.start()

    def tearDown(self):
        '''tearDown test'''
        return self.inst.stop()

    @staticmethod
    def listen_fn_mock():
        '''Mock for listen fn'''
        return mock.Mock(spec='__call__')

    @defer.inlineCallbacks
    def test_all_match(self):
        '''
        Test event handler is fired when all details match
        '''
        listen_fn = self.listen_fn_mock()

        yield self.inst.add_event_handler(listen_fn, 'during', username='bob', role='admin')
        event = 'some_event'

        yield self.inst.fire_event(event, username='bob', role='admin')

        listen_fn.assert_called_once_with(event)

    @defer.inlineCallbacks
    def test_no_match(self):
        '''
        Test handler doesn't fire when no details match
        '''
        listen_fn = self.listen_fn_mock()

        yield self.inst.add_event_handler(listen_fn, 'during', username='bob', role='admin')
        event = 'some_event'

        yield self.inst.fire_event(event, username='susan', role='admin')

        self.assertFalse(listen_fn.called, 'function should not have been called')

    @defer.inlineCallbacks
    def test_partial_match(self):
        '''
        Test handler fires when one detail matches, and remaining details are unspecifed
        '''
        listen_fn = self.listen_fn_mock()

        yield self.inst.add_event_handler(listen_fn, 'during', role='admin')
        event = 'some_event'

        yield self.inst.fire_event(event, username='susan', role='admin')

        listen_fn.assert_called_once_with(event)

    @defer.inlineCallbacks
    def test_remove(self):
        '''
        Test a removed handler no longer fires
        '''
        listen_fn = self.listen_fn_mock()

        handle = yield self.inst.add_event_handler(
            listen_fn, 'during', username='bob', role='admin')
        event = 'some_event'

        yield self.inst.fire_event(event, username='bob', role='admin')

        yield self.inst.remove_event_handler(handle)

        listen_fn.assert_called_once_with(event)

    @defer.inlineCallbacks
    def test_auto_remove(self):
        '''
        Test that a function that is garbage collected no longer fires indicating it has
        been automatically removed from dispatcher
        '''
        listen_fn = self.listen_fn_mock()
        event = 'some_event'

        # Create lambda that can be deleted
        def listen_fn_wrapper(event):
            '''Just pass through to mock'''
            return listen_fn(event)

        yield self.inst.add_event_handler(
            listen_fn_wrapper, 'during', username='bob', role='admin')

        # Fire test
        yield self.inst.fire_event(event, username='bob', role='admin')
        listen_fn.assert_called_once_with(event)
        listen_fn.reset_mock()

        # Delete and fire again
        del listen_fn_wrapper

        yield self.inst.fire_event(event, username='bob', role='admin')

        self.assertFalse(listen_fn.called, 'function should not have been called')

    @defer.inlineCallbacks
    def test_auto_remove_with_instance_method(self):
        '''
        Test that a instance method that is garbage collected no longer fires indicating it has
        been automatically removed from dispatcher
        '''
        listen_fn = self.listen_fn_mock()
        event = 'some_event'

        # Create instance that can be deleted
        class TestClass(object):
            def listen_fn_wrapper(self, event):
                '''Just pass through to mock'''
                return listen_fn(event)

        inst = TestClass()

        yield self.inst.add_event_handler(
            inst.listen_fn_wrapper, 'during', username='bob', role='admin')

        # Fire test
        yield self.inst.fire_event(event, username='bob', role='admin')
        listen_fn.assert_called_once_with(event)
        listen_fn.reset_mock()

        # Delete and fire again
        del inst

        yield self.inst.fire_event(event, username='bob', role='admin')

        self.assertFalse(listen_fn.called, 'function should not have been called')

    @defer.inlineCallbacks
    def test_stop_start(self):
        '''
        Test that stopping and starting dispatcher prevent and allow handling as expected.
        '''
        listen_fn = self.listen_fn_mock()

        self.inst.add_event_handler(listen_fn, 'during', role='admin')
        event = 'some_event'
        self.inst.fire_event(event, username='susan', role='admin')

        yield self.inst.stop()

        listen_fn.assert_called_once_with(event)

        self.inst.fire_event(event, username='susan', role='admin')

        listen_fn.assert_called_once_with(event)

        self.inst.start()

        listen_fn.assert_called_once_with(event)

        yield self.inst.fire_event(event, username='susan', role='admin')

        self.assertEqual(listen_fn.call_count, 2)

    def test_invalid_spec(self):
        '''
        Test that specify a match spec that isn't present during setup raises an exception.
        '''
        listen_fn = self.listen_fn_mock()

        self.assertRaises(
            ValueError,
            self.inst.add_event_handler,
            listen_fn,
            'during',
            password='admin')
