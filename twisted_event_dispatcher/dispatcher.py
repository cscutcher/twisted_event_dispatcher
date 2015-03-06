# -*- coding: utf-8 -*-
"""
Random feedback thinger
"""
import collections
import logging
import weakref

DEV_LOGGER = logging.getLogger(__name__)


class EventListener(collections.Hashable):
    '''
    Represents single event handler
    '''
    def __init__(self, listen_fn, **other_kwargs):
        self.listen_fn = listen_fn
        self.details = other_kwargs
        self.id = id(self)

    def __hash__(self):
        return self.id


class EventDispatcher(object):
    '''
    Handles dispatching for abstract events

    :param indexes:
        Sequence of strings which represent keyword arguments to use as indexes for event
        dispatching.
    '''
    def __init__(self, valid_details):
        self._valid_details = tuple(valid_details)
        self._indexes = collections.defaultdict(self.index_factory)
        self._listeners = {}

    listener_factory = EventListener

    def index_factory(self):
        return collections.defaultdict(set)

    def add_listener(self, listen_fn, use_weakref=True, **expected_details):
        '''
        '''
        if use_weakref:
            orig_listen_fn = listen_fn
            listen_fn = weakref.proxy(listen_fn)

        expected_details = {key: expected_details.pop(key, None) for key in self._valid_details}

        listener_inst = self.listener_factory(listen_fn, **expected_details)
        self._listeners[listener_inst.id] = listener_inst

        for detail, filter in expected_details.iteritems():
            self._indexes[detail][filter].add(listener_inst)

        if use_weakref:
            # If we're using weakref automate removal of listeners when object
            # disappears.
            weakref.ref(
                orig_listen_fn, callback=(lambda _fn: self.remove_listener(listener_inst.id)))

        return listener_inst.id

    def remove_listener(self, listener_id):
        listener = self._listeners.pop(listener_id)

        for detail, filter in listener.details.iteritems():
            self._indexes[detail][filter].remove(listener_inst)

        del(listener)

    def _get_set_of_listeners(self, event_index, value):
        '''
        See which listeners match an event_index and value
        '''
        return self._indexes[event_index][None].union(self._indexes[event_index][value])

    def handle_event(self, event, **event_details):
        '''
        Handle incoming event
        '''
        filter_sets = [
            self._get_set_of_listeners(key, value) for key, value in event_details.iteritems()]

        if len(filter_sets) < 1:
            return defer.succeed()
        elif len(filter_sets) == 1:
            listeners = filter_sets[0]
        else:
            listeners = filter_sets[0].intersection(*(filter_sets[1:]))

        for listener in listeners:
            listener.listen_fn(event)
