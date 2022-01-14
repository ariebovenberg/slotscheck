Configuration
=============

``slotscheck`` can be configured through the command line options or a
project's ``pyproject.toml``.

Command line options
--------------------

See the :ref:`command line interface <cli>` documentation


``pyproject.toml``
------------------

The same configuration options are available in the ``pyproject.toml`` file.
If this file is not found in the current directory,
it's parent will be tried until the root is reached.
An example file:

.. code-block:: toml

   [tool.slotscheck]
   strict-imports = true
   exclude-modules = '''
   (
     .*\\.test\\..*
     |__main__
     |some\\.specific\\.module
   )
   '''
   require-superclass = false

Note that CLI options have precedence over ``pyproject.toml``.
Thus, you can always override what's configured.
