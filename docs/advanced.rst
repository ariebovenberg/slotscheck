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
     rev: v0.16.1
     hooks:
     - id: slotscheck
       # If your Python files are not importable from the project root,
       # (for example if they're in a "src" directory)
       # you will need to add this directory to Python's import path.
       # See slotscheck.rtfd.io/en/latest/discovery.html for more info.
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
