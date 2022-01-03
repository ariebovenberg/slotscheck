import urllib
from datetime import date
from decimal import Decimal
from enum import Enum
from fractions import Fraction
from random import Random

from slotscheck.common import SlotsStatus, slot_status, walk_classes


def test_walk_classes():
    assert len(set(walk_classes(urllib))) == 54


def test_slot_status():
    assert slot_status(type) is SlotsStatus.NOT_PUREPYTHON
    assert slot_status(tuple) is SlotsStatus.NOT_PUREPYTHON
    assert slot_status(dict) is SlotsStatus.NOT_PUREPYTHON
    assert slot_status(float) is SlotsStatus.NOT_PUREPYTHON
    assert slot_status(Decimal) is SlotsStatus.NOT_PUREPYTHON
    assert slot_status(Enum) is SlotsStatus.NO_SLOTS
    assert slot_status(Random) is SlotsStatus.NO_SLOTS
    assert slot_status(Fraction) is SlotsStatus.HAS_SLOTS
    assert slot_status(date) is SlotsStatus.NOT_PUREPYTHON
    assert slot_status(AssertionError) is SlotsStatus.NOT_PUREPYTHON
    assert slot_status(RuntimeError) is SlotsStatus.NOT_PUREPYTHON
