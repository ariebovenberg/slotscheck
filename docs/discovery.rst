Module discovery
================

To check files, slotscheck needs to import them. 
The process if importing files usually behaves as you would expect.
However, there are some complications that you may 
need to be aware of.

.. admonition:: Summary

   You should generally be fine if you follow these rules:

   - To check files in your current directory,
     you should run slotscheck as ``python -m slotscheck``.
   - To check files elsewhere, you may need to set the ``$PYTHONPATH``
     environment variable.

Whether you run ``python -m slotscheck`` or just ``slotscheck`` has an impact
on which files will be imported and checked.
This is not a choice by ``slotscheck``, but simply the way entry points work
in Python. When running ``python -m slotscheck``, the current working
directory is added to ``sys.path``, so any modules in the current directory
can be imported. This is not the case when running just ``slotscheck``.
So if you run ``slotscheck foo.py``, ``foo`` will not be importable.
In fact, if ``foo`` happens to be the name of an installed module,
``import foo`` will import that instead!
In that case ``slotscheck`` will refuse to run,
and print an informative message.
An alternative way to ensure the correct files can be imported is with the
``PYTHONPATH`` environment variable.

To illustrate all this, imagine the following file tree::

   src/
     foo/
       __init__.py
       bar.py

In this example:

- ❌ ``slotscheck src/foo/bar.py`` will result in an error, because ``src`` is
  not in ``sys.path``.
- ❌ ``slotscheck -m foo.bar`` will result in an error, because ``src`` is
  not in ``sys.path``.
- ❌ ``cd src && slotscheck foo/bar.py`` will also result in an error,
  because the current working directory is not in ``sys.path``.
- ❌ ``cd src && slotscheck -m foo.bar`` will also result in an error,
  because the current working directory is not in ``sys.path``.
- ✅ ``cd src && python -m slotscheck foo/bar.py`` will scan the ``foo.bar`` module as
  expected, because the current working directory *is* in the import path.
- ✅ ``cd src && python -m slotscheck -m foo.bar`` will scan the ``foo.bar`` module as
  expected, because the current working directory *is* in the import path.
- ✅ ``env PYTHONPATH=src slotscheck src/foo/bar.py`` will scan the ``foo.bar`` module
  as expected, because ``src`` is added to ``sys.path`` by environment variable.
- ✅ ``env PYTHONPATH=src slotscheck -m foo.bar`` will scan the ``foo.bar`` module
  as expected, because ``src`` is added to ``sys.path`` by environment variable.

Once the ``foo`` module is installed into site-packages,
the following behavior will change:
if ``foo/`` files are passed, but the installed module would be imported
instead, slotscheck will report an error.

.. admonition:: Why doesn't slotscheck just add the right paths
   to ``sys.path`` for me?

   Automatically changing ``sys.path`` is a global change that
   could have unintended consequences.
   In this case it's best not to assume this is the user's intention.
   Since you'll probably only need to add a single entry to Python's path,
   it's easy to define ``$PYTHONPATH`` explicitly.
