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
     rev: v0.6.0
     hooks:
     - id: slotscheck
       exclude: "^$"  # add files you don't want slotscheck to import

Namespace packages
------------------

Namespace packages come in `different flavors <https://packaging.python.org/en/latest/guides/packaging-namespace-packages/>`_.
When using the ``-m/--module`` flag in the CLI, all these flavors are supported.
When specifying file paths, *native* namespace packages are not supported.
