Configuration
=============

``slotscheck`` can be configured through the command line options or file
(``pyproject.toml`` or ``setup.cfg``).

Command line options
--------------------

See the :ref:`command line interface <cli>` documentation.

Configuration file
------------------

The ``pyproject.toml`` or ``setup.cfg`` files offer the same configuration
options as the CLI. See the :ref:`CLI docs <cli>`.

An example TOML configuration:

.. code-block:: toml

   [tool.slotscheck]
   strict-imports = true
   exclude-modules = '''
   (
     (^|\.)test_  # ignore any tests
     |^some\.specific\.module  # do not check his module
   )
   '''
   require-superclass = false

The equivalent ``setup.cfg``:

.. code-block:: cfg

   [slotscheck]
   strict-imports = true
   exclude-modules = (
       (^|\.)test_  # ignore any tests
       |^some\.specific\.module  # do not check his module
       )
   require-superclass = false

Slotscheck will first try to find a ``pyproject.toml`` with a ``tool.slotscheck``
section in the current working directory. If not found, it will try to find a
``setup.cfg`` with ``slotscheck`` section.
Until a file is found, this search will be repeated for each parent directory.

Alternatively, you can manually specify the config file to be used with the
``--settings`` config option.

Note that CLI options have precedence over a config file.
Thus, you can always override what's configured there.
