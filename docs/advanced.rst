Advanced topics
===============

Resolving imports
-----------------

.. admonition:: Summary

   You should run slotscheck as ``python -m slotscheck``
   to make sure it scans the right files. Or use ``PYTHONPATH`` for this.

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
   could have unintented consequences.
   In this case it's best not to *assume* this is the user's intention.
   In practice you'll probably only need to add a single entry to Python's path,
   so it's easy to define ``PYTHONPATH`` explicitly.

Pre-commit hook
---------------

You can run ``slotscheck`` as a pre-commit hook.
Use the following configuration:

.. warning::

   Slotscheck imports files to check them.
   Be sure to specify ``exclude``
   to prevent slotscheck from importing scripts unintentionally.


.. code-block:: yaml

   repos:
   - repo: https://github.com/ariebovenberg/slotscheck
     rev: v0.11.0
     hooks:
     - id: slotscheck
       # If your Python files are not importable from the project root,
       # (for example if they're in a "src" directory)
       # you will need to add this directory to Python's import path.
       # See "resolving imports" in the docs for more information.
       # Below is what you need to add if you're code isn't importable
       # from the project root, in a "src" directory:
       #
       # entry: env PYTHONPATH=src slotscheck --verbose


       # Add files you don't want slotscheck to import.
       # The example below ensures slotscheck will only run on
       # files in the "src/foo" directory:
       #
       # exclude: "^(?!src/foo/)"

       # For slotscheck to be able to import the code,
       # it needs access to the same dependencies.
       # One way is to use `additional_dependencies`.
       # These will then be added to the isolated slotscheck pre-commit env.
       # An example set of requirements is given below:
       #
       # additional_dependencies:
       # - requests==2.26
       # - click~=8.0

       # Instead of `additional_dependencies`, you can reuse the currently
       # active environment by setting language to `system`.
       # This requires `slotscheck` to be installed in that environment.
       #
       # language: system


Namespace packages
------------------

Namespace packages come in `different flavors <https://packaging.python.org/en/latest/guides/packaging-namespace-packages/>`_.
When using the ``-m/--module`` flag in the CLI, all these flavors are supported.
When specifying file paths, *native* namespace packages are not supported.
