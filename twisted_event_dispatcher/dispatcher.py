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
    @staticmethod
    def _null_func(event):
        pass

    def __init__(self, listen_fn, phase, use_weakref, remove_callback, **other_kwargs):
        self.details = other_kwargs
        self.id = id(self)
        self.phase = phase

        if use_weakref:
            self._listen_fn = None
            self._listen_ref = weakref.ref(listen_fn, lambda _fn: remove_callback(self.id))
        else:
            self._listen_fn = listen_fn
            self._listen_ref = None


    @property
    def listen_fn(self):
        if self._listen_fn is not None:
            return self._listen_fn

        deref = self._listen_ref()
        if deref is None:
            return self._null_func
        else:
            return deref

    def __hash__(self):
        return self.id


class EventDispatcher(object):
    '''
    Handles dispatching for abstract events

    :param indexes:
        Sequence of strings which represent keyword arguments to use as indexes for event
        dispatching.
    '''
    def __init__(self, valid_details, phases=('before', 'during', 'after')):
        self._valid_details = tuple(valid_details)
        self._indexes = collections.defaultdict(self.index_factory)
        self._listeners = {}
        self._phases = tuple(phases)

    listener_factory = EventListener

    @staticmethod
    def index_factory():
        return collections.defaultdict(set)

    def add_listener(self, listen_fn, phase, use_weakref=True, **expected_details):
        '''
        '''
        expected_details = {key: expected_details.pop(key, None) for key in self._valid_details}

        listener_inst = self.listener_factory(
            listen_fn,
            phase=phase,
            use_weakref=use_weakref,
            remove_callback=self.remove_listener,
            **expected_details)
        self._listeners[listener_inst.id] = listener_inst

        for detail, filter in expected_details.iteritems():
            self._indexes[detail][filter].add(listener_inst)

        return listener_inst.id

    def remove_listener(self, listener_id):
        listener = self._listeners.pop(listener_id)

        for detail, filter in listener.details.iteritems():
            self._indexes[detail][filter].remove(listener)

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

        phase_dict = collections.defaultdict(list)

        for listener in listeners:
            phase_dict[listener.phase].append(listener)

        for phase in self._phases:
            for listener in phase_dict[phase]:
                listener.listen_fn(event)