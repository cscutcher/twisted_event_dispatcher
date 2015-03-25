# twisted_event_dispatcher
[![Build Status](https://travis-ci.org/cscutcher/twisted_event_dispatcher.svg)](https://travis-ci.org/cscutcher/twisted_event_dispatcher)

https://github.com/cscutcher/twisted_event_dispatcher

`twisted_event_dispatcher` is an experimental generic event dispatcher written for twisted.

Copyright Cisco Systems International 2015

Example Usage
=============

Say we want to build a event dispatcher that notifies a subsytem when a new user is created.

Ignore this setup for doctest.
```python
>>> from oni.twisted_event_dispatcher import EventDispatcher
>>> from twisted.internet import defer
>>> from crochet import wait_for, setup; setup() # We need crochet to make the doctest work
>>> @wait_for(timeout=5.0)
... def wait_for_result(deferred):
...     return deferred

```

First we create an instance of EventDispatcher to handle these events.

```python
>>> user_event_dispatcher = EventDispatcher(
...     allowed_match_spec_keywords=('event_type','user','role'))

```

You could register this with the zope component architecture as a utility providing
IEventDispatcher or store it by some other means.

Elsewhere in your code you can now add a handler. Something that wants to be notified when a new
user is created.

We define something that will get called with our event.

```python
>>> calls = []
>>> def notify_admin(user_event):
...      # Pretend this is sending an email
...      calls.append(user_event)
...      # and pretend that this is an asyncronous function
...      return defer.succeed(None)
...

```

Then we register the handler with the dispatcher. It'll give us an id we can use later to remove
the handler.

```python
>>> handler_id = wait_for_result(user_event_dispatcher.add_event_handler(notify_admin, 'during'))

```

Then imagine we get a new user called bob. We construct an object that will contain the information
the handler needs. In this case we'll user a named tuple

```python
>>> from collections import namedtuple
>>> UserEvent = namedtuple('UserEvent', ('event_type', 'user', 'role', 'other_data'))
>>> event = UserEvent('user_created', 'bob', 'user', '1234')

```

We need to start the dispatcher before it'll actually notify handlers.

```python
>>> user_event_dispatcher.start()

```

Now we fire the event. Note we have to pass details manually.

```python
>>> result = wait_for_result(user_event_dispatcher.fire_event(
...     event, event_type=event.event_type, role=event.role, user=event.user))
>>> calls
[UserEvent(event_type='user_created', user='bob', role='user', other_data='1234')]

```

Lets fire a second event;
```python
>>> event = UserEvent('user_created', 'susan', 'admin', '4567')
>>> result = wait_for_result(user_event_dispatcher.fire_event(
...     event, event_type=event.event_type, role=event.role, user=event.user))
>>> calls # doctest: +NORMALIZE_WHITESPACE
[UserEvent(event_type='user_created', user='bob', role='user', other_data='1234'), 
 UserEvent(event_type='user_created', user='susan', role='admin', other_data='4567')]

```

We can remove the handler to ensure we're no longer notified.

Let's empty our call dict;
```python
>>> calls[:] = []

```

Now remove the handler;
```python
>>> wait_for_result(user_event_dispatcher.remove_event_handler(handler_id))

```

If we fire another event now nothing should happen;

```python
>>> event = UserEvent('user_created', 'susan', 'admin', '4567')
>>> result = wait_for_result(user_event_dispatcher.fire_event(
...     event, event_type=event.event_type, role=event.role, user=event.user))
>>> calls
[]

```

What if we want a handler that only fires for events when role == 'user'.
We can do this by specifying a match spec when we add the handler.

```python
>>> handler_id = wait_for_result(user_event_dispatcher.add_event_handler(
...     notify_admin, 'during', role='user'))

```

Now if we fire with an admin user we shouldn't get triggered.

```python
>>> event = UserEvent('user_created', 'susan', 'admin', '4567')
>>> result = wait_for_result(user_event_dispatcher.fire_event(
...     event, event_type=event.event_type, role=event.role, user=event.user))
>>> calls
[]

```

but if we fire with a normal user we will be triggered.

```python
>>> event = UserEvent('user_created', 'bob', 'user', '1234')
>>> result = wait_for_result(user_event_dispatcher.fire_event(
...     event, event_type=event.event_type, role=event.role, user=event.user))
>>> calls
[UserEvent(event_type='user_created', user='bob', role='user', other_data='1234')]

```



Rationale
=========

This aims to add capability similar to the fireSystemEvent and addSystemEventTrigger methods on
IReactorCore but with some more capability.

I'm still working out exactly what I want to achieve, but I have noticed on multiple occasions
I have ended up having to develop an event dispatcher for specific scenarios, and in each
case I find myself rediscovering the same bugs and edge cases.
I hope by implementing a more generic and flexible reusable module I can avoid this in the future.

What currently exists?
----------------------
Ideally I'd like to use something that already exists. This is what I've considered and why
they are currently not quite right.

#### Use subscription adapters from the zope component architecture ####

I like ZCA but having to use a different interface everytime I want to only fire some of the
handlers feels to inflexible.

#### zope.event ####

As far as I can tell you always fire all of your events. I think I'm missing something.
More research needed.

#### Twisted reactor fireSystemEvent ####

Does most of what I want but I find the only having eventType as the filter condition when
firing handlers is limiting.

#### pydispatcher and py-notify ####

Both look interesting. No support for deferreds built in,
but it'd probably be easy enough to wrap.

Worth researching if just for inspiration.


Implementation
==============
The code in this repo is a experimental implementation to allow me to think about what I want
and play around some.

At the moment it;
* Allow different callables to be triggered depending on more than just eventType string.
  So for example say we have an event that fires when a new users been added we could have
  callbacks that would fire on every new user, or just when users of certain roles fire.
* Allow more than just three phases.
* All phases will wait for deferreds to callback before starting the next phase.

I'd also like to;
* Add callbacks that would fires N times before removing itself.
* Maybe allow the keys that can be specified in match spec to be changed after object is init.
* Improve the general efficiency.

Why 99 characters instead of 79
-------------------------------
Forgive me Guido for I have sinned. I find 79 characters restrictive so I prefer to use 99 for
my projects if I can.


