# -*- coding: utf-8 -*-
"""
Deferred Helpers
"""
import logging
import functools

from twisted.internet import defer

DEV_LOGGER = logging.getLogger(__name__)


class InstanceMethodLockDecorator(object):
    '''
    Like the standard lock_decorator but lock exists for each instance of the instance bound to
    instancemethod

    :param lock_name: Name of lock to use on instance
    '''
    def __init__(self, lock_name):
        self._lock_name = lock_name

    def wrapped_function_cb(self, _lock_result, orig_function, lock, instance, *args, **kwargs):
        '''
        Callback that calls original function after lock is acquired and then adds lock release
        callback
        '''
        DEV_LOGGER.debug('Acquired method lock %r on %r', self._lock_name, instance)
        result_deferred = defer.maybeDeferred(orig_function, instance, *args, **kwargs)
        result_deferred.addBoth(self.lock_release_cb, lock, instance)
        return result_deferred

    def lock_release_cb(self, result, lock, instance):
        '''
        Callback that releases lock
        '''
        DEV_LOGGER.debug('Releasing method lock %r on %r', self._lock_name, instance)
        lock.release()
        return result

    def __call__(self, orig_function):
        lock_name = self._lock_name
        wrapped_function_cb = self.wrapped_function_cb

        def wrapped_function(self, *args, **kwargs):
            '''
            Wrapped function to lock method
            '''
            try:
                lock = getattr(self, lock_name)
            except AttributeError:
                lock = defer.DeferredLock()
                setattr(self, lock_name, lock)
                DEV_LOGGER.debug('Created method lock %r on %r', lock_name, self)

            DEV_LOGGER.debug('Acquiring method lock %r on %r', lock_name, self)
            lock_deferred = lock.acquire()
            lock_deferred.addCallback(
                wrapped_function_cb, orig_function, lock, self, *args, **kwargs)
            return lock_deferred

        return functools.wraps(orig_function)(wrapped_function)

instance_method_lock = InstanceMethodLockDecorator
