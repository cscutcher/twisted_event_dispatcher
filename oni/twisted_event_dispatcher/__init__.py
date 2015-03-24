# -*- coding: utf-8 -*-
'''
Establish external interface of twisted_event_dispatcher

Example use;

Say we want to build a event dispatcher that notifies a subsytem when a new user is created.

Ignore this setup for doctest.

>>> from twisted.internet import defer
>>> from crochet import wait_for, setup; setup() # We need crochet to make the doctest work
>>> @wait_for(timeout=5.0)
... def wait_for_result(deferred):
...     return deferred

First we create an instance of EventDispatcher to handle these events.

>>> user_event_dispatcher = EventDispatcher(
...     allowed_match_spec_keywords=('event_type','user','role'))

You could register this with the zope component architecture as a utility providing
IEventDispatcher or store it by some other means.

Elsewhere in your code you can now add a handler. Something that wants to be notified when a new
user is created.

We define something that will get called with our event.

>>> calls = []
>>> def notify_admin(user_event):
...      # Pretend this is sending an email
...      calls.append(user_event)
...      # and pretend that this is an asyncronous function
...      return defer.succeed(None)
...

Then we register the handler with the dispatcher. It'll give us an id we can use later to remove
the handler.

>>> handler_id = wait_for_result(user_event_dispatcher.add_event_handler(notify_admin, 'during'))

Then imagine we get a new user called bob. We construct an object that will contain the information
the handler needs. In this case we'll user a named tuple

>>> from collections import namedtuple
>>> UserEvent = namedtuple('UserEvent', ('event_type', 'user', 'role', 'other_data'))
>>> event = UserEvent('user_created', 'bob', 'user', '1234')

We need to start the dispatcher before it'll actually notify handlers.
>>> user_event_dispatcher.start()

Now we fire the event. Note we have to pass details manually.

>>> result = wait_for_result(user_event_dispatcher.fire_event(
...     event, event_type=event.event_type, role=event.role, user=event.user))
>>> calls
[UserEvent(event_type='user_created', user='bob', role='user', other_data='1234')]

Lets fire a second event;
>>> event = UserEvent('user_created', 'susan', 'admin', '4567')
>>> result = wait_for_result(user_event_dispatcher.fire_event(
...     event, event_type=event.event_type, role=event.role, user=event.user))
>>> calls
[UserEvent(event_type='user_created', user='bob', role='user', other_data='1234'),\
 UserEvent(event_type='user_created', user='susan', role='admin', other_data='4567')]

We can remove the handler to ensure we're no longer notified.

Let's empty our call dict;
>>> calls[:] = []

Now remove the handler;
>>> wait_for_result(user_event_dispatcher.remove_event_handler(handler_id))

If we fire another event now nothing should happen;
>>> event = UserEvent('user_created', 'susan', 'admin', '4567')
>>> result = wait_for_result(user_event_dispatcher.fire_event(
...     event, event_type=event.event_type, role=event.role, user=event.user))
>>> calls
[]

What if we want a handler that only fires for events when role == 'user'.
We can do this by specifying a match spec when we add the handler.

>>> handler_id = wait_for_result(user_event_dispatcher.add_event_handler(
...     notify_admin, 'during', role='user'))

Now if we fire with an admin user we shouldn't get triggered.

>>> event = UserEvent('user_created', 'susan', 'admin', '4567')
>>> result = wait_for_result(user_event_dispatcher.fire_event(
...     event, event_type=event.event_type, role=event.role, user=event.user))
>>> calls
[]

but if we fire with a normal user we will be triggered.
>>> event = UserEvent('user_created', 'bob', 'user', '1234')
>>> result = wait_for_result(user_event_dispatcher.fire_event(
...     event, event_type=event.event_type, role=event.role, user=event.user))
>>> calls
[UserEvent(event_type='user_created', user='bob', role='user', other_data='1234')]


'''
# flake8 doesn't like imports below without use
# flake8: noqa

from oni.twisted_event_dispatcher._dispatcher import EventDispatcher
from oni.twisted_event_dispatcher.interfaces import IEventDispatcher
from oni.twisted_event_dispatcher.interfaces import IBackgroundUtility
