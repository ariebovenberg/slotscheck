import sys
from importlib import import_module
from typing import List
from unittest import mock

import pytest

from slotscheck.discovery import (
    FailedImport,
    FoundModule,
    Module,
    ModuleNotPurePython,
    ModuleTree,
    Package,
    consolidate,
    find_modules,
    module_tree,
    walk_classes,
)

from .conftest import EXAMPLES_DIR


def fset(*args) -> frozenset:
    return frozenset(args)


def make_pkg(name: str, *content) -> Package:
    return Package(name, frozenset(content))


class TestWalkClasses:
    def test_module_does_not_exist(self):
        [result] = walk_classes(Module("cannot_import"))
        assert isinstance(result, FailedImport)
        assert result == FailedImport("cannot_import", mock.ANY)

        with pytest.raises(ModuleNotFoundError, match="cannot_import"):
            raise result.exc

    def test_module_import_raises_other_error(self):
        [_, _, result] = list(
            walk_classes(
                make_pkg("module_misc", make_pkg("a", Module("evil")))
            )
        )
        assert isinstance(result, FailedImport)
        assert result == FailedImport("module_misc.a.evil", mock.ANY)

        with pytest.raises(BaseException, match="Can't import this!"):
            raise result.exc

    def test_module_import_raises_keyboardinterrupt(self, mocker):
        mocker.patch(
            "importlib.import_module", side_effect=KeyboardInterrupt("foo")
        )
        with pytest.raises(KeyboardInterrupt, match="foo"):
            next(walk_classes(make_pkg("module_misc", Module("a"))))

    def test_single_module(self):
        [result] = list(walk_classes(Module("module_singular")))

        import module_singular  # type: ignore

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
                )
            )
        )
        assert len(result) == 7

        import module_misc  # type: ignore

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
        assert tree == make_pkg(
            "module_misc",
            make_pkg(
                "a",
                make_pkg(
                    "b",
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
        )
        assert len(list(tree)) == len(tree) == 9
        assert (
            tree.display()
            == """\
module_misc
 a
  b
   __main__
   c
   mypy
    bla
    foo
     z"""
        )

    def test_submodule(self):
        tree = module_tree("module_misc.a.b.c")
        assert tree == make_pkg(
            "module_misc",
            make_pkg("a", make_pkg("b", Module("c"))),
        )

    def test_namespaced(self):
        assert module_tree("namespaced.module") == make_pkg(
            "namespaced", make_pkg("module", Module("foo"), Module("bla"))
        )

    def test_implicitly_namspaced(self):
        assert module_tree("implicitly_namespaced.module") == make_pkg(
            "implicitly_namespaced",
            make_pkg("module", Module("foo"), Module("bla")),
        )

    def test_not_inspectable(self):
        with pytest.raises(ModuleNotPurePython):
            module_tree("builtins")

    def test_does_not_exist(self):
        with pytest.raises(ModuleNotFoundError):
            module_tree("doesnt_exist")

    def test_module(self):
        assert module_tree("module_singular") == Module("module_singular")


class TestFilterName:
    def test_module(self):
        assert Module("foo").filtername(lambda _: True) == Module("foo")
        assert Module("foo").filtername(lambda _: False) is None
        assert Module("foo").filtername(lambda s: s.startswith("f")) == Module(
            "foo"
        )
        assert Module("foo").filtername(lambda s: s.startswith("b")) is None

    def test_package(self):
        package = Package(
            "a",
            fset(
                Module("a"),
                Module("b"),
                Package(
                    "c",
                    fset(Module("a"), Package("b", fset(Module("a")))),
                ),
                Package(
                    "d",
                    fset(
                        Package(
                            "a",
                            fset(
                                Module("a"),
                                Package(
                                    "b", fset(Package("a", fset(Module("x"))))
                                ),
                            ),
                        ),
                        Module("z"),
                        Module("b"),
                    ),
                ),
            ),
        )
        result = package.filtername(lambda x: "b.a" not in x)

        assert result == Package(
            "a",
            fset(
                Module("a"),
                Module("b"),
                Package(
                    "c",
                    fset(Module("a"), Package("b", fset())),
                ),
                Package(
                    "d",
                    fset(
                        Package(
                            "a",
                            fset(Module("a"), Package("b", fset())),
                        ),
                        Module("z"),
                        Module("b"),
                    ),
                ),
            ),
        )

        assert package.filtername(lambda _: False) is None


def _import(m: FoundModule):
    sys.path.insert(0, str(m.location))
    try:
        import_module(m.name)
    finally:
        sys.path.remove(str(m.location))


class TestFindModules:
    def test_given_directory_without_python(self):
        assert list(find_modules(EXAMPLES_DIR / "files/another")) == []

    def test_given_nonpython_file(self):
        assert list(find_modules(EXAMPLES_DIR / "files/foo")) == []

    def test_given_python_file(self):
        location = EXAMPLES_DIR / "files/subdir/some_module/../myfile.py"
        result = list(find_modules(location))
        assert result == [FoundModule("myfile", location.parent)]
        for m in result:
            _import(m)

    def test_given_python_root_module(self):
        location = EXAMPLES_DIR / "files/subdir/some_module/"
        result = list(find_modules(location))
        assert result == [FoundModule("some_module", location.parent)]
        for m in result:
            _import(m)

    def test_given_dir_containing_python_files(self):
        location = EXAMPLES_DIR / "files/my_scripts/sub/.."
        result = list(find_modules(location))
        assert len(result) == 4
        assert set(result) == {
            FoundModule("bla", location),
            FoundModule("foo", location),
            FoundModule("foo", location / "sub"),
            FoundModule("mymodule", location),
        }
        for m in result:
            _import(m)

    def test_given_file_within_module(self):
        location = EXAMPLES_DIR / "files/subdir/some_module/sub/foo.py"
        result = list(find_modules(location))
        assert result == [
            FoundModule("some_module.sub.foo", EXAMPLES_DIR / "files/subdir")
        ]
        for m in result:
            _import(m)

    def test_given_submodule(self):
        location = EXAMPLES_DIR / "files/subdir/some_module/sub/../sub"
        result = list(find_modules(location))
        assert result == [
            FoundModule("some_module.sub", location.resolve().parents[1])
        ]
        for m in result:
            _import(m)

    def test_given_init_py(self):
        location = (
            EXAMPLES_DIR / "files/subdir/some_module/sub/../sub/__init__.py"
        )
        result = list(find_modules(location))
        assert result == [
            FoundModule("some_module.sub", location.resolve().parents[2])
        ]
        for m in result:
            _import(m)


class TestConsolidate:
    def test_empty(self):
        assert list(consolidate(iter([]))) == []

    @pytest.mark.parametrize(
        "tree",
        [
            Module("foo"),
            Package("foo", fset(Module("bla"), Package("qux", fset()))),
            Package("bar", fset(Module("bla"), Package("qux", fset()))),
        ],
    )
    def test_one_module(self, tree: ModuleTree):
        assert list(consolidate(iter([tree]))) == [tree]

    def test_distinct_modules(self):
        trees: List[ModuleTree] = [
            Module("foo"),
            Package("bar", fset(Module("bla"), Package("qux", fset()))),
            Module("bla"),
            Package("buzz", fset()),
            Module("qux"),
        ]
        result = list(consolidate(iter(trees)))
        assert len(result) == 5
        assert set(result) == set(trees)

    def test_module_and_package(self):
        trees: List[ModuleTree] = [
            Module("foo"),
            Package("foo", fset(Module("foo"), Module("bar"))),
        ]
        assert list(consolidate(iter(trees))) == [
            Package("foo", fset(Module("foo"), Module("bar"))),
        ]
        assert list(consolidate(reversed(trees))) == [
            Package("foo", fset(Module("foo"), Module("bar"))),
        ]


class TestMergeTrees:
    def test_no_overlap(self):
        with pytest.raises(ValueError, match="shared components"):
            Module("foo").merge(Module("bar"))

        with pytest.raises(ValueError, match="shared components"):
            Package("foo", fset(Module("bar"))).merge(Package("bar", fset()))

    def test_same_module(self):
        assert Module("foo").merge(Module("foo")) == Module("foo")

    def test_package_override_module(self):
        assert Package("foo", fset(Module("bar"))).merge(
            Module("foo")
        ) == Package("foo", fset(Module("bar")))
        assert Module("foo").merge(
            Package("foo", fset(Module("bar")))
        ) == Package("foo", fset(Module("bar")))

    def test_same_packages(self):
        package = Package(
            "foo", fset(Package("bar", fset(Module("bla"), Module("foo"))))
        )
        assert package.merge(package) == package

    @pytest.mark.parametrize(
        "a, b, expect",
        [
            (
                Package(
                    "foo",
                    fset(
                        Module("foo"),
                    ),
                ),
                Package("foo", fset()),
                Package(
                    "foo",
                    fset(
                        Module("foo"),
                    ),
                ),
            ),
            (
                Package(
                    "a",
                    fset(
                        Package(
                            "b",
                            fset(
                                Module("z"),
                            ),
                        ),
                        Module("c"),
                    ),
                ),
                Package(
                    "a",
                    fset(
                        Package(
                            "c",
                            fset(
                                Module("y"),
                            ),
                        )
                    ),
                ),
                Package(
                    "a",
                    fset(
                        Package(
                            "b",
                            fset(
                                Module("z"),
                            ),
                        ),
                        Package(
                            "c",
                            fset(
                                Module("y"),
                            ),
                        ),
                    ),
                ),
            ),
            (
                Package(
                    "a",
                    fset(
                        Package(
                            "b",
                            fset(
                                Module("z"),
                            ),
                        ),
                        Module("c"),
                    ),
                ),
                Package(
                    "a",
                    fset(
                        Package(
                            "b",
                            fset(
                                Module("y"),
                            ),
                        )
                    ),
                ),
                Package(
                    "a",
                    fset(
                        Package(
                            "b",
                            fset(
                                Module("z"),
                                Module("y"),
                            ),
                        ),
                        Module("c"),
                    ),
                ),
            ),
        ],
    )
    def test_different_packages(self, a, b, expect):
        assert a.merge(b) == expect
        assert b.merge(a) == expect
