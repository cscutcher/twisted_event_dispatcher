# -*- coding: utf-8 -*-
'''
Establish external interface of twisted_event_dispatcher
'''
# flake8 doesn't like imports below without use
# flake8: noqa
from oni.twisted_event_dispatcher._dispatcher import EventDispatcher
from oni.twisted_event_dispatcher.interfaces import IEventDispatcher
from oni.twisted_event_dispatcher.interfaces import IBackgroundUtility
