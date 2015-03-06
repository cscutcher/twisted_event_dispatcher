# -*- coding: utf-8 -*-
"""
Tests for twisted_event_dispatcher module
"""
import logging
import unittest
import mock

from twisted_event_dispatcher import EventDispatcher

DEV_LOGGER = logging.getLogger(__name__)

class TestEventDispatcher(unittest.TestCase):
    '''
    Test EventDispatcher
    '''
    factory = EventDispatcher

    def test_all_match(self):
        inst = self.factory(('username', 'role'))
        listen_fn = mock.Mock()

        handle = inst.add_listener(listen_fn, 'during', username='bob', role='admin')
        event = 'some_event'

        inst.handle_event(event, username='bob', role='admin')

        listen_fn.assert_called_once_with(event)

    def test_no_match(self):
        inst = self.factory(('username', 'role'))
        listen_fn = mock.Mock()

        handle = inst.add_listener(listen_fn, 'during', username='bob', role='admin')
        event = 'some_event'

        inst.handle_event(event, username='susan', role='admin')

        self.assertFalse(listen_fn.called, 'function should not have been called')

    def test_partial_match(self):
        inst = self.factory(('username', 'role'))
        listen_fn = mock.Mock()

        handle = inst.add_listener(listen_fn, 'during', role='admin')
        event = 'some_event'

        inst.handle_event(event, username='susan', role='admin')

        listen_fn.assert_called_once_with(event)
