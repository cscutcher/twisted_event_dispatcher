# -*- coding: utf-8 -*-
"""
Contains primary implementation of IEventDispatcher
"""
import collections
import logging
import weakref

from zope.interface import implementer
from twisted.internet import defer

from oni.twisted_event_dispatcher._deferred_helpers import (
    instance_method_lock)
from oni.twisted_event_dispatcher.interfaces import IEventDispatcher
from oni.twisted_event_dispatcher.interfaces import IBackgroundUtility

DEV_LOGGER = logging.getLogger(__name__)


class _CallableWeakProxy(object):
    '''
    Weakref proxy type class for just holding a callable. If the referent dissapears the function
    will return None and ignore arguments
    '''
    def __init__(self, orig_fn):
        self.weakref = weakref.ref(orig_fn)

    def __call__(self, *args, **kwargs):
        callable = self.weakref()
        if callable is None:
            return None
        else:
            return callable(*args, **kwargs)


class _MethodWeakProxy(object):
    '''
    Weakref proxy type class for just holding a bound method.
    The weakref is actual setup on the instance not the method itself.
    If the referent dissapears the function will return None and ignore arguments
    '''
    def __init__(self, orig_method):
        self.weakref = weakref.ref(orig_method.im_self)
        self.fn = orig_method.im_func

    def __call__(self, *args, **kwargs):
        inst = self.weakref()
        if inst is None:
            return None
        else:
            return self.fn(inst, *args, **kwargs)


class _EventHandlerRegistrationEntry(collections.Hashable):
    '''
    Stores single event handler
    '''
    def __init__(self, listen_fn, phase, use_weakref, remove_callback, **other_kwargs):
        self.details = other_kwargs
        self.id = id(self)
        self.phase = phase
        self.remove_callback = remove_callback

        if use_weakref:
            if hasattr(listen_fn, 'im_self'):
                # This case we have a bound instance method. Weakref the instance not the method
                weakref.ref(listen_fn.im_self, self._auto_remove)
                self.listen_fn = _MethodWeakProxy(listen_fn)
            else:
                weakref.ref(listen_fn, self._auto_remove)
                self.listen_fn = _CallableWeakProxy(listen_fn)
        else:
            self.listen_fn = listen_fn

    def _auto_remove(self, _weakref):
        '''
        Function to auto remove self with weakrefs
        '''
        DEV_LOGGER.debug('Auto removing %r', self)
        return self.remove_callback(self.id)

    def __hash__(self):
        return self.id

    def __repr__(self):
        return (
            '<{inst.__class__.__module__}.{inst.__class__.__name__}'
            '(id={inst.id!r}, listen_fn={inst.listen_fn!r}, phase={inst.phase!r}, '
            'details={inst.details!r})>').format(inst=self)


@implementer(IBackgroundUtility, IEventDispatcher)
class EventDispatcher(object):
    '''
    Handles dispatching for abstract events

    :param allowed_match_spec_keywords:
        Sequence of strings which represent keyword arguments to allow when adding event handlers.

    After initialisation an instance will be in the stopped state until .start() is called.
    '''
    _registration_factory = _EventHandlerRegistrationEntry

    def __init__(self, allowed_match_spec_keywords, phases=('before', 'during', 'after')):
        self._allowed_match_spec_keywords = tuple(allowed_match_spec_keywords)
        self._indexes = collections.defaultdict(self._index_factory)
        self._event_handlers = {}
        self._phases = tuple(phases)
        self._event_handler_modification_lock = defer.DeferredLock()
        self._running = False

    def start(self):
        '''
        Restart a stopped EventDispatcher
        '''
        DEV_LOGGER.debug('Starting EventDispatcher %r', self)
        self._running = True

    def stop(self):
        '''
        Stop the EventDispatcher so that no more new events are processed until start is called
        again.

        :returns: Deferred that will callback when the EventDispatcher has stopped as is quiescent.
        '''
        DEV_LOGGER.debug('Stopping EventDispatcher %r', self)
        self._running = False
        return self._event_handler_modification_lock.acquire().addCallback(
            lambda lock: lock.release())

    @property
    def running(self):
        '''RO property for running'''
        return self._running

    @staticmethod
    def _index_factory():
        '''
        Create new factory
        '''
        return collections.defaultdict(set)

    def add_event_handler(self, listen_fn, phase, use_weakref=True, **match_spec):
        '''
        See :py:func:`IEventDispatcher.add_event_handler`
        '''
        match_spec_complete = {
            key: match_spec.pop(key, None) for key in self._allowed_match_spec_keywords}

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
        DEV_LOGGER.debug(
            'Registering event handler: %r', event_handler_inst)
        self._event_handlers[event_handler_inst.id] = event_handler_inst
        for detail, detail_filter in event_handler_inst.details.iteritems():
            self._indexes[detail][detail_filter].add(event_handler_inst)
        return event_handler_inst.id

    @instance_method_lock('_event_handler_modification_lock')
    def remove_event_handler(self, event_handler_id):
        '''
        See :py:func:`IEventDispatcher.remove_event_handler`
        '''
        DEV_LOGGER.debug('Removing event handler with id %r', event_handler_id)
        event_handler = self._event_handlers.pop(event_handler_id)

        for detail, filter_inst in event_handler.details.iteritems():
            self._indexes[detail][filter_inst].remove(event_handler)

        del(event_handler)

    def _get_set_of_event_handlers(self, event_index, value):
        '''
        See which event_handlers match an event_index and value
        '''
        return self._indexes[event_index][None].union(self._indexes[event_index][value])

    @instance_method_lock('_event_handler_modification_lock')
    def fire_event(self, event, **event_details):
        '''
        See :py:func:`IEventDispatcher.fire_event`
        '''
        DEV_LOGGER.debug(
            'Firing for event %r with details %r',
            event,
            event_details)

        if not self.running:
            DEV_LOGGER.warning('Event %r received but dispatcher is not running')
            return defer.succeed(None)

        filter_sets = [
            self._get_set_of_event_handlers(key, value)
            for key, value in event_details.iteritems()]

        DEV_LOGGER.debug('Found %r filter_sets', len(filter_sets))

        if len(filter_sets) < 1:
            return defer.succeed(None)
        elif len(filter_sets) == 1:
            event_handlers = filter_sets[0]
        else:
            event_handlers = filter_sets[0].intersection(*(filter_sets[1:]))

        phase_dict = collections.defaultdict(list)

        for event_handler in event_handlers:
            phase_dict[event_handler.phase].append(event_handler)

        return self._run_phase(None, iter(self._phases), phase_dict, event)

    @classmethod
    def _run_phase(cls, _result, phase_iter, phase_dict, event):
        '''
        Run the next phase of event handlers
        '''
        try:
            phase = phase_iter.next()
        except StopIteration:
            return defer.succeed(None)

        DEV_LOGGER.debug(
            'Running phase %r for event %r. Contains %r',
            phase,
            event,
            phase_dict[phase])

        phase_deferreds = [
            defer.maybeDeferred(event_handler.listen_fn, event)
            for event_handler in phase_dict[phase]]

        return defer.DeferredList(phase_deferreds).addCallback(
            cls._run_phase, phase_iter, phase_dict, event)
