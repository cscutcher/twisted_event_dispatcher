# -*- coding: utf-8 -*-
"""
Interfaces for twisted_event_dispatcher
"""
import logging
import zope.interface

DEV_LOGGER = logging.getLogger(__name__)


class IBackgroundUtility(zope.interface.Interface):
    '''
    Interface for utility that has some background operation that can be started and stopped
    '''
    running = zope.interface.Attribute('Bool that is true when utility is in running state')

    def start():
        '''
        Start utility.
        Before this point the utility will generate no asynchronous events
        (and so may not function).

        :return: Deferred which will call back when this utility has been started.
        '''

    def stop():
        '''
        Stop a utility.
        After the deferred this function returns calls back. No more asynchronous events will
        be generated by this utility.

        :return: Deferred which will call back when this utility has been stopped.
        '''


class IEventDispatcher(zope.interface.Interface):
    '''
    Handles dispatching for abstract events
    '''
    def add_event_handler(listen_fn, phase, use_weakref=True, **match_spec):
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

    def remove_event_handler(event_handler_id):
        '''
        Remove a handlers registration so it's no longer fired.

        :param event_handler_id: Reference that was returned when adding the handler.
        :returns: Deferred that will callback when registration has been removed.
        '''

    def handle_event(event, **event_details):
        '''
        Handle incoming event. Any relevant details that might affect the handlers that will be
        triggered should be passed as **event_details
        '''
