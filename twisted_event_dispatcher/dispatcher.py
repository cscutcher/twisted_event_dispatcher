# -*- coding: utf-8 -*-
"""
Random feedback thinger
"""
import collections
import logging
import weakref

from twisted.internet import defer

from twisted_event_dispatcher.deferred_helpers import instance_method_lock

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
        '''
        Property to get the listen function that copes with weakref if present.

        :returns: Callable that takes event arguent
        '''
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
        self._listener_modification_lock = defer.DeferredLock()
        self._state = 'running'

    listener_factory = EventListener


    def start(self):
        self._state = 'running'

    def stop(self):
        self._state = 'stopped'
        return self._listener_modification_lock.acquire().addCallback(lambda lock: lock.release())

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

        return self._register_listener(listener_inst)

    @instance_method_lock('_listener_modification_lock')
    def _register_listener(self, listener_inst):
        self._listeners[listener_inst.id] = listener_inst
        for detail, filter in listener_inst.details.iteritems():
            self._indexes[detail][filter].add(listener_inst)
        return listener_inst.id

    @instance_method_lock('_listener_modification_lock')
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

    @instance_method_lock('_listener_modification_lock')
    def handle_event(self, event, **event_details):
        '''
        Handle incoming event
        '''
        if self._state == 'stopped':
            return defer.succeed(None)

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

        return self._run_phase(None, iter(self._phases), phase_dict, event)

    @staticmethod
    def _phase_errback(failure, event, phase, listener):
        DEV_LOGGER.error(
            'Got failure: %r when triggering listener %r on phase %r with event %r',
            failure,
            event,
            phase,
            listener)
        return None

    @classmethod
    def _run_phase(cls, _result, phase_iter, phase_dict, event):
        try:
            phase = phase_iter.next()
        except StopIteration:
            return defer.succeed(None)

        phase_deferreds = [
            defer.maybeDeferred(listener.listen_fn, event).addErrback(cls._phase_errback)
            for listener in phase_dict[phase]]

        return defer.DeferredList(phase_deferreds).addCallback(
            cls._run_phase, phase_iter, phase_dict, event)

