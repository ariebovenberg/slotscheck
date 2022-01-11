Changelog
=========

0.3.2 (2022-01-10)
------------------

- Recognize builtin exceptions as not having slots.

0.3.1 (2022-01-10)
------------------

- Catch ``BaseException`` in module import.

0.3.0 (2022-01-10)
------------------

- Add ``--strict-imports`` flag (#24)
- Detect overlapping slots (#10)
- 100% test coverage (#15)
- Add ``--exclude`` flag (#9)

0.2.1 (2022-01-04)
------------------

- Improved error message if module cannot be found (#18)

0.2.0 (2022-01-03)
------------------

- Enable running with ``-m slotscheck`` (#13)

0.1.2 (2022-01-03)
------------------

- Skip ``__main__.py`` in module scan to prevent running unintented code

0.1.1 (2022-01-03)
------------------

- Improve output report

0.1.0 (2020-12-30)
------------------

- Improve documentation

0.0.1 (2021-12-29)
------------------

- Initial release
