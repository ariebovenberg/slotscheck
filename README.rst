✅ Slotscheck
=============

.. image:: https://img.shields.io/pypi/v/slotscheck.svg?style=flat-square
   :target: https://pypi.python.org/pypi/slotscheck

.. image:: https://img.shields.io/pypi/l/slotscheck.svg?style=flat-square
   :target: https://pypi.python.org/pypi/slotscheck

.. image:: https://img.shields.io/pypi/pyversions/slotscheck.svg?style=flat-square
   :target: https://pypi.python.org/pypi/slotscheck

.. image:: https://img.shields.io/readthedocs/slotscheck.svg?style=flat-square
   :target: http://slotscheck.readthedocs.io/

.. image:: https://img.shields.io/badge/code%20style-black-000000.svg?style=flat-square
   :target: https://github.com/psf/black

Adding ``__slots__`` to a class in Python is a great way to reduce memory usage.
But to work properly, all base classes need to implement it.
It turns out it's easy to forget one class in complex inheritance trees.
What's worse: there is nothing warning you that you messed up.

*Until now!*

Quickstart
----------

Usage is quick from the command line:

.. code-block:: bash

   slotscheck [MODULE]


For example:

.. code-block:: bash

   $ slotscheck pandas
   incomplete slots in 'pandas.core.internals.blocks.Block'
   incomplete slots in 'pandas.core.internals.blocks.NumericBlock'
   incomplete slots in 'pandas.core.internals.blocks.ObjectBlock'
   incomplete slots in 'pandas.core.internals.array_manager.SingleArrayManager'
   incomplete slots in 'pandas.core.internals.managers.SingleBlockManager'
   incomplete slots in 'pandas.core.internals.array_manager.BaseArrayManager'
   incomplete slots in 'pandas.core.internals.array_manager.SingleArrayManager'
   incomplete slots in 'pandas.core.internals.blocks.Block'
   incomplete slots in 'pandas.core.internals.blocks.CategoricalBlock'
   incomplete slots in 'pandas.core.internals.blocks.DatetimeLikeBlock'
   incomplete slots in 'pandas.core.internals.blocks.NumericBlock'
   incomplete slots in 'pandas.core.internals.blocks.ObjectBlock'
   incomplete slots in 'pandas.core.internals.managers.BaseBlockManager'
   incomplete slots in 'pandas.core.internals.managers.SingleBlockManager'

Limitations
-----------

- Even in the case that slots are not inherited properly,
  there may still an advantage to using them
  (i.e. attribute access speed and *some* memory savings)
- Only classes at module-level are checked (i.e. no nested classes)
- In rare cases imports may fail, the module is then skipped. This is logged.

Installation
------------

It's available on PyPI.

.. code-block:: bash

  pip install slotscheck
