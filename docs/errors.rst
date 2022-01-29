Errors and violations
=====================

Slotscheck detects several different problems with slots.

Superclass has no slots
-----------------------

In order for memory savings from ``__slots__`` to work fully,
all base classes of a slotted classe need to define slots as well:

.. code-block:: python

   class NoSlots:
       pass

   class HasSlots:
       __slots__ = ()


   class Bad(NoSlots):
       __slots__ = ('x', 'y')

   class Good(HasSlots):
       __slots__ = ('x', 'y')


You can see the memory impact of this mistake with ``pympler`` library:

.. code-block:: python

   from pympler.asizeof import asizeof

   asizeof(Bad())  # 168
   asizeof(Good())  # 48


In addition, if a superclass has no slots, all subclasses will get ``__dict__``,
which allows setting of arbitrary attributes.

.. code-block:: python

   Bad().foo = 5  # no error, even though `foo` is not a slot!
   Good().foo = 3  # raises AttributeError, as it should.


Overlapping slots
-----------------

If a class defines a slot also present in a base class,
the slot in the base class becomes inaccessible.
This can cause surprising behavior.
What's worse: these inaccessible slots do take up space in memory!

.. code-block:: python

   class Base:
       __slots__ = ('x', )

   class Bad(Base):
       __slots__ = ('x', 'z')

   class Good(Base):
       __slots__ = ('z', )


The official Python docs has this to say about overlapping slots
(emphasis mine):

   If a class defines a slot also defined in a base class,
   the instance variable defined by the base class slot is inaccessible
   (except by retrieving its descriptor directly from the base class).
   **This renders the meaning of the program undefined.** In the future,
   a check may be added to prevent this.

Duplicate slots
---------------

Python doesn't stop you from declaring the same slot multiple times.
This mistake will cost you some memory:

.. code-block:: python

   class Good:
       __slots__ = ('a', 'b')

    class Bad:
       __slots__ = ('a', 'a', 'a', 'b', 'a', 'b')


    asizeof(Good())  # 48
    asizeof(Bad())  # 80
