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

The benchmark below shows the difference in memory usage:

.. code-block:: python

   import tracemalloc as tm

   tm.start()
   _ = [Good() for _ in range(1_000_000)]
   print(f"Allocated {tm.get_traced_memory()[0] // 1_000_000} MB for Good")

   tm.start()
   _ = [Bad() for _ in range(1_000_000)]
   print(f"Allocated {tm.get_traced_memory()[0] // 1_000_000} MB for Bad")

Which will print:

.. code-block:: text

    Allocated 56 MB for Good
    Allocated 96 MB for Bad


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


    sys.getsizeof(Good())  # 48
    sys.getsizeof(Bad())  # 80

Unused slots (Experimental)
---------------------------

.. note::

   This check is **experimental** and requires **Python 3.13+**.
   Enable it with the ``--detect-unused-slots`` flag or
   ``detect-unused-slots = true`` in your configuration.

Slots that are declared but never assigned within the class body
are likely dead code or indicate a refactoring oversight.

.. code-block:: python

   class Bad:
       __slots__ = ('x', 'y', 'unused')

       def __init__(self):
           self.x = 1
           self.y = 2

   class Good:
       __slots__ = ('x', 'y')

       def __init__(self):
           self.x = 1
           self.y = 2

Abstract classes and Protocol classes are excluded from this check,
since their slots are expected to be assigned by subclasses or
implementors.

The special slots ``__weakref__`` and ``__dict__`` are also excluded,
as they serve Python-internal purposes rather than user assignment.

**Known limitation:** This check uses Python 3.13's ``__static_attributes__``
to determine which attributes are assigned within the class body.
Attributes that are only set externally (e.g. ``obj.slot = value``
from outside the class) will be reported as unused. Use
``--exclude-slots`` with a regex pattern to suppress such false positives.
