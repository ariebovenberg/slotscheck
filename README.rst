🎰 Slotscheck
=============

.. image:: https://img.shields.io/pypi/v/slotscheck.svg?color=blue
   :target: https://pypi.python.org/pypi/slotscheck

.. image:: https://img.shields.io/pypi/l/slotscheck.svg
   :target: https://pypi.python.org/pypi/slotscheck

.. image:: https://img.shields.io/pypi/pyversions/slotscheck.svg
   :target: https://pypi.python.org/pypi/slotscheck

.. image:: https://img.shields.io/readthedocs/slotscheck.svg
   :target: http://slotscheck.readthedocs.io/

.. image:: https://github.com/ariebovenberg/slotscheck/actions/workflows/build.yml/badge.svg
   :target: https://github.com/ariebovenberg/slotscheck/actions/workflows/build.yml

.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
   :target: https://github.com/psf/black

Adding ``__slots__`` to a class in Python is a great way to reduce memory usage.
But to work properly, all base classes need to implement it.
It turns out it's easy to forget one class in complex inheritance trees.
What's worse: there is nothing warning you that you messed up.

✨ *Until now!* ✨

See my `blog post <https://dev.arie.bovenberg.net/blog/finding-broken-slots-in-popular-python-libraries/>`_
for the longer story behind ``slotscheck``.

Quickstart
----------

Usage is quick from the command line:

.. code-block:: bash

   slotscheck [MODULE]


For example:

.. code-block:: bash

   $ slotscheck pandas
   ERROR: 'pandas.core.internals.array_manager:BaseArrayManager' has slots but inherits from non-slot class.
   ERROR: 'pandas.core.internals.array_manager:SingleArrayManager' defines overlapping slots.
   ERROR: 'pandas.core.internals.array_manager:SingleArrayManager' has slots but inherits from non-slot class.
   ERROR: 'pandas.core.internals.blocks:Block' has slots but inherits from non-slot class.
   ERROR: 'pandas.core.internals.blocks:CategoricalBlock' has slots but inherits from non-slot class.
   ERROR: 'pandas.core.internals.blocks:DatetimeLikeBlock' has slots but inherits from non-slot class.
   ERROR: 'pandas.core.internals.blocks:NumericBlock' has slots but inherits from non-slot class.
   ERROR: 'pandas.core.internals.blocks:ObjectBlock' has slots but inherits from non-slot class.
   ERROR: 'pandas.core.internals.managers:BaseBlockManager' has slots but inherits from non-slot class.
   ERROR: 'pandas.core.internals.managers:SingleBlockManager' has slots but inherits from non-slot class.
   Oh no, found some problems!

Now get to fixing --
and add ``slotscheck`` to your CI pipeline to prevent mistakes from creeping in again!

Use the ``--help`` option to find out more.


Could this be a flake8 plugin?
------------------------------

Maybe. But it'd be a lot of work.

The problem is that flake8 plugins need to work without running the code.
Many libraries use conditional imports, star imports, re-exports,
and define slots with decorators or metaclasses.
This all but requires running the code to determine the class tree and slots.

There's `an issue <https://github.com/ariebovenberg/slotscheck/issues/6>`_
to track any progress on the matter.

Notes
-----

- ``slotscheck`` will try to import all submodules of the given package.
  If there are scripts without ``if __name__ == "__main__":`` blocks,
  they may be executed.
- Even in the case that slots are not inherited properly,
  there may still be an advantage to using them
  (i.e. attribute access speed and *some* memory savings).
  However, I've found in most cases this is unintentional.
- Limited to the CPython implementation for now.
- Non pure-Python classes are currently assumed to have slots.
  This is not necessarily the case, but it is nontrivial to determine.

Installation
------------

It's available on PyPI.

.. code-block:: bash

  pip install slotscheck
