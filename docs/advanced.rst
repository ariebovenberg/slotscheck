Advanced topics
===============

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
     rev: v0.7.2
     hooks:
     - id: slotscheck
       # Add files you don't want slotscheck to import.
       # For example, "^(?!src/)" ensures slotscheck will only run on
       # files in the "src" directory.
       exclude: "^$"


Namespace packages
------------------

Namespace packages come in `different flavors <https://packaging.python.org/en/latest/guides/packaging-namespace-packages/>`_.
When using the ``-m/--module`` flag in the CLI, all these flavors are supported.
When specifying file paths, *native* namespace packages are not supported.

``python -m slotscheck`` vs ``slotscheck``
------------------------------------------

Running as ``python -m slotscheck`` allows slotscheck to import files
from your current working directory. Running bare ``slotscheck`` will
most likely import the *installed* version of the code, which may be different!
