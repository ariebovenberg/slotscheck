.. _cli:

Command line interface
======================

.. code-block:: text

   usage: slotscheck [-h] [-m MODULE]
                     [--require-superclass | --no-require-superclass]
                     [--require-subclass | --no-require-subclass]
                     [--include-modules INCLUDE_MODULES]
                     [--exclude-modules EXCLUDE_MODULES]
                     [--include-classes INCLUDE_CLASSES]
                     [--exclude-classes EXCLUDE_CLASSES]
                     [--strict-imports | --no-strict-imports]
                     [--detect-unused-slots | --no-detect-unused-slots]
                     [--exclude-slots EXCLUDE_SLOTS] [-v]
                     [--settings SETTINGS] [--version]
                     [FILES ...]

   Check whether your __slots__ are working properly.

   positional arguments:
     FILES

   options:
     -h, --help            show this help message and exit
     -m, --module MODULE   Check this module. Cannot be combined with FILES
                           argument. Can be repeated multiple times to scan
                           several modules.
     --require-superclass, --no-require-superclass
                           Report an error when a slots class inherits from a
                           non-slotted (or __dict__) class.
     --require-subclass, --no-require-subclass
                           Report an error when a non-slotted class inherits
                           from a slotted class.
     --include-modules INCLUDE_MODULES
                           A regular expression that matches modules to include.
     --exclude-modules EXCLUDE_MODULES
                           A regular expression that matches modules to exclude.
     --include-classes INCLUDE_CLASSES
                           A regular expression that matches classes to include.
     --exclude-classes EXCLUDE_CLASSES
                           A regular expression that matches classes to exclude.
     --strict-imports, --no-strict-imports
                           Treat failed imports as errors.
     --detect-unused-slots, --no-detect-unused-slots
                           Detect slots that are never assigned within the class
                           body. Requires Python 3.13+.
     --exclude-slots EXCLUDE_SLOTS
                           A regular expression matching slots to exclude from
                           unused-slot detection.
     -v, --verbose         Display extra descriptive output.
     --settings SETTINGS   Path to the configuration file to use.
     --version             show program's version number and exit
