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


class _EventHandlerRegistrationEntry(collections.Hashable):
    '''
    Represents single event handler
    '''
    @staticmethod
    def _null_func(event):
        '''
        Null handler function that is used when the real function has since disappeared
        but the _EventHandlerRegistrationEntry hasn't been removed from EventDispatcher
        '''
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

        # It's possible that this _EventHandlerRegistrationEntry can be triggered after the
        #  listen_fn has been gc'd but before the weakref has triggered the remove in the
        #  EventDispatcher. This handles this scenario by calling a null handler.
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
    _registration_factory = _EventHandlerRegistrationEntry

    def __init__(self, valid_details, phases=('before', 'during', 'after')):
        self._valid_details = tuple(valid_details)
        self._indexes = collections.defaultdict(self._index_factory)
        self._event_handlers = {}
        self._phases = tuple(phases)
        self._event_handler_modification_lock = defer.DeferredLock()
        self._state = 'running'

    def start(self):
        '''
        Restart a stopped EventDispatcher
        '''
        self._state = 'running'

    def stop(self):
        '''
        Stop the EventDispatcher so that no more new events are processed until start is called
        again.

        :returns: Deferred that will callback when the EventDispatcher has stopped as is quiescent.
        '''
        self._state = 'stopped'
        return self._event_handler_modification_lock.acquire().addCallback(
            lambda lock: lock.release())

    @staticmethod
    def _index_factory():
        return collections.defaultdict(set)

    def add_event_handler(self, listen_fn, phase, use_weakref=True, **match_spec):
        '''
        Add new event handler

        :param callable listen_fn:
            Callable to call when a new event is received and detail specification matches.

        :param phase:
            Phase to trigger handler. Set in self._phases. Usually before, during, after.
            All handlers in a phase are triggered concurrently and the next phase's wont be
            triggered until the last phase finished.

        :param bool use_weakref:
            Use a weakref when storing the listen_fn.
            This will mean that the functions registration as an event handler will not prevent
            the function being garbage collected by python. If it is garbage collected the
            handler registration will be automatically removed.

        :param **match_spec:
            Detail specification.
            The handler will only be triggered if all details match this specification.
            None (details) indicated trigger whatever the value of the detail is.

        :returns:
            Deferred that will callback when handler has been successfully added with an id
            that can be used to remove the handlers registration.
        '''
        match_spec_complete = {key: match_spec.pop(key, None) for key in self._valid_details}

        if len(match_spec):
            raise ValueError('Got unexpected match_spec: {!r}'.format(match_spec))

        event_handler_inst = self._registration_factory(
            listen_fn,
            phase=phase,
            use_weakref=use_weakref,
            remove_callback=self.remove_event_handler,
            **match_spec_complete)

        return self._register_event_handler(event_handler_inst)

    @instance_method_lock('_event_handler_modification_lock')
    def _register_event_handler(self, event_handler_inst):
        '''
        Used internally to actually store the registration and set up any indexes.
        '''
        self._event_handlers[event_handler_inst.id] = event_handler_inst
        for detail, filter in event_handler_inst.details.iteritems():
            self._indexes[detail][filter].add(event_handler_inst)
        return event_handler_inst.id

    @instance_method_lock('_event_handler_modification_lock')
    def remove_event_handler(self, event_handler_id):
        '''
        Remove a handlers registration so it's no longer fired.

        :param event_handler_id: Reference that was returned when adding the handler.
        :returns: Deferred that will callback when registration has been removed.
        '''
        event_handler = self._event_handlers.pop(event_handler_id)

        for detail, filter in event_handler.details.iteritems():
            self._indexes[detail][filter].remove(event_handler)

        del(event_handler)

    def _get_set_of_event_handlers(self, event_index, value):
        '''
        See which event_handlers match an event_index and value
        '''
        return self._indexes[event_index][None].union(self._indexes[event_index][value])

    @instance_method_lock('_event_handler_modification_lock')
    def handle_event(self, event, **event_details):
        '''
        Handle incoming event. Any relevant details that might affect the handlers that will be
        triggered should be passed as **event_details
        '''
        if self._state == 'stopped':
            return defer.succeed(None)

        filter_sets = [
            self._get_set_of_event_handlers(key, value)
            for key, value in event_details.iteritems()]

        if len(filter_sets) < 1:
            return defer.succeed()
        elif len(filter_sets) == 1:
            event_handlers = filter_sets[0]
        else:
            event_handlers = filter_sets[0].intersection(*(filter_sets[1:]))

        phase_dict = collections.defaultdict(list)

        for event_handler in event_handlers:
            phase_dict[event_handler.phase].append(event_handler)

        return self._run_phase(None, iter(self._phases), phase_dict, event)

    @staticmethod
    def _phase_errback(failure, event, phase, event_handler):
        '''
        Consume any errors and log.
        '''
        DEV_LOGGER.error(
            'Got failure: %r when triggering event_handler %r on phase %r with event %r',
            failure,
            event,
            phase,
            event_handler)
        return None

    @classmethod
    def _run_phase(cls, _result, phase_iter, phase_dict, event):
        '''
        Run the next phase of event handlers
        '''
        try:
            phase = phase_iter.next()
        except StopIteration:
            return defer.succeed(None)

        phase_deferreds = [
            defer.maybeDeferred(event_handler.listen_fn, event).addErrback(cls._phase_errback)
            for event_handler in phase_dict[phase]]

        return defer.DeferredList(phase_deferreds).addCallback(
            cls._run_phase, phase_iter, phase_dict, event)
