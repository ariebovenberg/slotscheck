Configuration
=============

``slotscheck`` can be configured through the command line options or a
project's ``pyproject.toml``.

Command line options
--------------------

See the :ref:`command line interface <cli>` documentation.


``pyproject.toml``
------------------

The ``pyproject.toml`` file offers the same configuration options as the CLI.
See the :ref:`CLI docs <cli>`. An example TOML configuration:

.. code-block:: toml

   [tool.slotscheck]
   strict-imports = true
   exclude-modules = '''
   (
     .*\.test\..*  # ignore any test code
     |__main__
     |some\.specific\.module  # this specific module has bad slots
   )
   '''
   require-superclass = false

If ``pyproject.toml`` is not found in the current directory,
it's parent will be tried until the root of the filesystem is reached.
Note that CLI options have precedence over ``pyproject.toml``.
Thus, you can always override what's configured there.
