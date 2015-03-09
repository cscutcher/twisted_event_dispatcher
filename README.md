# twisted_event_dispatcher

This aims to add capability similar to the fireSystemEvent and addSystemEventTrigger methods on
IReactorCore but with some more capability.

I'm still working out exactly what I want to achieve, but I have noticed on multiple occasions
I have ended up having to develop an event dispatcher for specific scenarios, and in each
case I find myself rediscovering the same bugs and edge cases. 
I hope by implementing a more generic and flexible reusable module I can avoid this in the future.

What currently exists?
======================
Ideally I'd like to use something that already exists. This is what I've considered and why
they are currently not quite right.

Use subscription adapters from the zope component architecture
--------------------------------------------------------------
I like ZCA but having to use a different interface everytime I want to only fire some of the 
handlers feels to inflexible. 

zope.event
----------
As far as I can tell you always fire all of your events. I think I'm missing something.
More research needed.

Twisted reactor fireSystemEvent
-------------------------------
Does most of what I want but I find the only having eventType as the filter condition when 
firing handlers is limiting.

pydispatcher and py-notify
---------------------------
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
