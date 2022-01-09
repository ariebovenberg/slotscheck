from unittest import mock

import pytest

from slotscheck.discovery import (
    FailedImport,
    Module,
    ModuleNotPurePython,
    Package,
    module_tree,
    walk_classes,
)


def fset(*args) -> frozenset:
    return frozenset(args)


class TestWalkClasses:
    def test_module_does_not_exist(self):
        [result] = walk_classes(Module("cannot_import"), parent_name=None)
        assert isinstance(result, FailedImport)
        assert result == FailedImport("cannot_import", mock.ANY)

        with pytest.raises(ModuleNotFoundError, match="cannot_import"):
            raise result.exc

    def test_module_import_raises_other_error(self):
        [result] = walk_classes(Module("module_misc.a.evil"), parent_name=None)
        assert isinstance(result, FailedImport)
        assert result == FailedImport("module_misc.a.evil", mock.ANY)

        with pytest.raises(RuntimeError, match="Can't import this!"):
            raise result.exc

    def test_single_module(self):
        [result] = list(
            walk_classes(Module("module_singular"), parent_name=None)
        )

        import module_singular

        assert result == fset(
            module_singular.A,
            module_singular.B,
            module_singular.B.C,
            module_singular.B.C.D,
            module_singular.E,
        )

    def test_package(self):
        result = list(
            walk_classes(
                Package(
                    "module_misc",
                    fset(
                        Module("__main__"),
                        Module("s"),
                        Package(
                            "doesnt_exist",
                            fset(Module("foo"), Package("g", fset())),
                        ),
                        Package(
                            "a",
                            fset(
                                Package(
                                    "evil",
                                    fset(
                                        Module("foo"),
                                        Package("sub", fset(Module("w"))),
                                    ),
                                ),
                                Module("z"),
                            ),
                        ),
                    ),
                ),
                parent_name=None,
            )
        )
        assert len(result) == 7

        import module_misc

        assert set(result) == {
            fset(
                module_misc.A,
                module_misc.B,
            ),
            fset(
                module_misc.a.U,
            ),
            fset(
                module_misc.s.K,
                module_misc.s.K.A,
                module_misc.s.Y,
            ),
            fset(
                module_misc.__main__.Z,
            ),
            fset(module_misc.a.z.W, module_misc.a.z.Q),
            FailedImport("module_misc.a.evil", mock.ANY),
            FailedImport("module_misc.doesnt_exist", mock.ANY),
        }


class TestModuleTree:
    def test_package(self):
        tree = module_tree("module_misc")
        assert tree == Package(
            "module_misc",
            fset(
                Module("__main__"),
                Module("s"),
                Package(
                    "a",
                    fset(
                        Module("z"),
                        Package(
                            "evil",
                            fset(
                                Module("foo"),
                                Package("sub", fset(Module("w"))),
                            ),
                        ),
                        Package(
                            "b",
                            fset(
                                Module("__main__"),
                                Module("c"),
                                Package(
                                    "mypy",
                                    fset(
                                        Module("bla"),
                                        Package("foo", fset(Module("z"))),
                                    ),
                                ),
                            ),
                        ),
                        Package(
                            "pytest",
                            fset(
                                Package("a", fset()),
                                Package("c", fset(Module("foo"))),
                            ),
                        ),
                    ),
                ),
            ),
        )

        assert len(list(tree)) == len(tree) == 20

    def test_subpackage(self):
        tree = module_tree("module_misc.a.b")
        assert tree == Package(
            "module_misc.a.b",
            fset(
                Module("__main__"),
                Module("c"),
                Package(
                    "mypy",
                    fset(
                        Module("bla"),
                        Package("foo", fset(Module("z"))),
                    ),
                ),
            ),
        )
        assert len(list(tree)) == len(tree) == 7
        assert (
            tree.display()
            == """\
module_misc.a.b
 __main__
 c
 mypy
  bla
  foo
   z"""
        )

    def test_namespaced(self):
        assert module_tree("namespaced.module") == Package(
            "namespaced.module",
            fset(Module("foo")),
        )

    def test_not_inspectable(self):
        with pytest.raises(ModuleNotPurePython):
            module_tree("builtins")

    def test_does_not_exist(self):
        with pytest.raises(ModuleNotFoundError):
            module_tree("doesnt_exist")

    def test_module(self):
        assert module_tree("module_singular") == Module("module_singular")
