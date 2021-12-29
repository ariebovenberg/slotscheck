import urllib

import slotscheck


def test_classes_in_module():
    assert (
        len(list(slotscheck._classes_in_module(urllib, verbose=False))) == 55
    )
