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


   class A(NoSlots):  # BAD
       __slots__ = ('x', 'y')

   class B(HasSlots):  # GOOD
       __slots__ = ('x', 'y')


In addition, if a superclass has no slots, you lose the restriction on 
setting arbitrary attributes:

.. code-block:: python

   A().foo = 5  # this is not prevented!
   B().foo = 3  # raises AttributeError, as it should


Overlapping slots
-----------------

If a class defines a slots also present in a base class,
the slot in the base class becomes inaccessible.
This can cause surprising behavior. 
What's worse: these inaccessible slots do take up space in memory!

.. code-block:: python

   class Base:
       __slots__ = ('x', )

   class A(Base):
       __slots__ = ('x', 'z')  # BAD: 'x' overlaps!

   class B(Base):
       __slots__ = ('z', )  # GOOD: 'x' is inherited from 'Base'
