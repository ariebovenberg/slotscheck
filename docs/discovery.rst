Module discovery
================

Slotscheck needs to import your code to check it.
If it can't, it suggests which directory to add to Python's import path::

   ERROR: File '/home/user/project/src/foo/bar.py' is not in PYTHONPATH.
   Try setting PYTHONPATH=src, or passing --pythonpath src

Either works. As a rule of thumb:

- To check files in the current directory (or below it), run slotscheck as
  ``python -m slotscheck``.
- To check files anywhere else, pass ``--pythonpath``, or set the
  ``$PYTHONPATH`` environment variable.

That is all you need to know.
If the suggestion didn't work, see `What about implicit namespace packages?`_.
The rest of this page explains why slotscheck can't find the directory
on its own.

Why the import path matters
---------------------------

Python, not slotscheck, decides which files can be imported,
based on how you start slotscheck.
``python -m slotscheck`` adds the current directory to ``sys.path``,
so modules there can be imported. Bare ``slotscheck`` does not.

So if you run ``slotscheck foo.py``, ``foo`` is not importable.
In fact, if ``foo`` is also the name of an installed module,
``import foo`` imports that instead!
In that case slotscheck refuses to run rather than check the wrong files.

Take this file tree::

   src/
     foo/
       __init__.py
       bar.py

Each command below tries to check ``foo/bar.py``.

.. list-table::
   :header-rows: 1

   * - Command
     - Result
   * - ``slotscheck src/foo/bar.py``
     - ❌ ``src`` is not in ``sys.path``
   * - ``cd src && slotscheck foo/bar.py``
     - ❌ bare ``slotscheck`` doesn't add the current directory to ``sys.path``
   * - ``cd src && python -m slotscheck foo/bar.py``
     - ✅ ``python -m`` adds the current directory to ``sys.path``
   * - ``slotscheck --pythonpath src src/foo/bar.py``
     - ✅ ``--pythonpath`` adds ``src`` to ``sys.path``
   * - ``env PYTHONPATH=src slotscheck src/foo/bar.py``
     - ✅ ``$PYTHONPATH`` adds ``src`` to ``sys.path``

The results are the same with ``-m foo.bar`` in place of the file path.

What about implicit namespace packages?
---------------------------------------

To pick the directory to suggest, slotscheck walks up from your file until
it reaches a directory without an ``__init__.py``.
An implicit namespace package (:pep:`420`) has no ``__init__.py``,
so slotscheck can't tell it apart from an ordinary directory.
The suggestion then stops one level too deep. Given this tree::

   src/
     mycompany/       <- a namespace package: no __init__.py
       tools/
         __init__.py

slotscheck suggests ``src/mycompany``, and with that path your code imports
as ``tools`` rather than ``mycompany.tools``.
Pass ``--pythonpath src`` instead, so that modules get their proper names.

.. admonition:: Why doesn't slotscheck just add the right paths
   to ``sys.path`` for me?

   ``sys.path`` is global: changing it affects every import in the process.
   A wrong guess wouldn't merely fail to help---it would change how
   *your own code* imports its dependencies, as the namespace package case
   above shows. So slotscheck doesn't guess.
   Since you'll probably need only a single entry, pass ``--pythonpath``
   (or set ``$PYTHONPATH``) yourself; slotscheck suggests the likely directory.
