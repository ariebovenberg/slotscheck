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
But to work properly, all subclasses need to implement it.
It turns out it's easy to forget one class in complex inheritance trees.
What's worse: there is nothing warning you that you messed up.
Until now!

Quickstart
----------

Usage is quick from the command line:

.. code-block:: bash

   $ slotscheck <my module name>

Installation
------------

It's available on PyPI.

.. code-block:: bash

  pip install slotscheck

Limitations
-----------

- Only classes at module-level are checked (i.e. no nested classes)
- In rare cases imports may fail, the module is then skipped. This is logged.
