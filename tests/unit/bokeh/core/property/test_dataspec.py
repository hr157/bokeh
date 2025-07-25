#-----------------------------------------------------------------------------
# Copyright (c) Anaconda, Inc., and Bokeh Contributors.
# All rights reserved.
#
# The full license is in the file LICENSE.txt, distributed with this software.
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Boilerplate
#-----------------------------------------------------------------------------
from __future__ import annotations # isort:skip

import pytest ; pytest

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------

# Standard library imports
import datetime
import warnings
from copy import copy

# External imports
import numpy as np
import pandas as pd

# Bokeh imports
from bokeh.core.has_props import HasProps, Local
from bokeh.core.property.vectorization import (
    Field,
    Value,
    field,
    value,
)
from bokeh.util.deprecation import BokehDeprecationWarning
from tests.support.util.api import verify_all

# Module under test
import bokeh.core.property.dataspec as bcpd # isort:skip

#-----------------------------------------------------------------------------
# Setup
#-----------------------------------------------------------------------------

ALL = (
    'AlphaSpec',
    'AngleSpec',
    'BoolSpec',
    'ColorSpec',
    'DashPatternSpec',
    'DataSpec',
    'DistanceSpec',
    'FloatSpec',
    'FontSizeSpec',
    'FontStyleSpec',
    'HatchPatternSpec',
    'IntSpec',
    'LineCapSpec',
    'LineJoinSpec',
    'MarkerSpec',
    'NumberSpec',
    'SizeSpec',
    'StringSpec',
    'TextAlignSpec',
    'TextBaselineSpec',
)

#-----------------------------------------------------------------------------
# General API
#-----------------------------------------------------------------------------

def test_strict_dataspec_key_values() -> None:
    for typ in (bcpd.NumberSpec, bcpd.StringSpec, bcpd.FontSizeSpec, bcpd.ColorSpec, bcpd.SizeSpec):
        class Foo(HasProps, Local):
            x = typ("x")
        f = Foo()
        with pytest.raises(ValueError):
            f.x = dict(field="foo", units="junk")

def test_dataspec_dict_to_serializable() -> None:
    for typ in (bcpd.NumberSpec, bcpd.StringSpec, bcpd.FontSizeSpec, bcpd.ColorSpec):
        class Foo(HasProps, Local):
            x = typ("x")
        foo = Foo(x=dict(field='foo'))
        props = foo.properties_with_values(include_defaults=False)
        assert isinstance(props['x'], Field)
        assert props['x'].field == 'foo'
        assert props['x'] is foo.x


class Test_AngleSpec:
    def test_default_value(self) -> None:
        class Foo(HasProps):
            x = bcpd.AngleSpec(default=14)

        a = Foo()

        assert a.x == 14
        assert a.x_units == 'rad'

    def test_setting_dict_sets_units(self) -> None:
        class Foo(HasProps):
            x = bcpd.AngleSpec(default=14)

        a = Foo()

        assert a.x == 14
        assert a.x_units == 'rad'

        a.x = {'value': 180, 'units': 'deg'}
        assert a.x == value(180)
        assert a.x_units == 'deg'

    def test_setting_json_sets_units_keeps_dictness(self) -> None:
        class Foo(HasProps):
            x = bcpd.AngleSpec(default=14)

        a = Foo()

        assert a.x == 14
        assert a.x_units == 'rad'

        a.set_from_json('x', {'value': 180, 'units': 'deg'})
        assert a.x == 180
        assert a.x_units == 'deg'

    def test_setting_dict_does_not_modify_original_dict(self) -> None:
        class Foo(HasProps):
            x = bcpd.AngleSpec(default=14)

        a = Foo()

        assert a.x == 14
        assert a.x_units == 'rad'

        new_value = {'value': 180, 'units': 'deg'}
        new_value_copy = copy(new_value)
        assert new_value_copy == new_value

        a.x = new_value
        assert a.x == value(180)
        assert a.x_units == 'deg'

        assert new_value_copy == new_value


class Test_BoolSpec:
    def test_is_valid(self) -> None:
        prop = bcpd.BoolSpec(default=True)

        assert prop.is_valid(False)
        assert prop.is_valid(True)

        assert not prop.is_valid(0)
        assert not prop.is_valid(1)

class Test_ColorSpec:
    def test_field(self) -> None:
        class Foo(HasProps):
            col = bcpd.ColorSpec("colorfield")
        desc = Foo.__dict__["col"]
        f = Foo()
        assert f.col == "colorfield"
        assert desc.get_value(f) == Field("colorfield")
        f.col = "myfield"
        assert f.col == "myfield"
        assert desc.get_value(f) == Field("myfield")

    def test_field_default(self) -> None:
        class Foo(HasProps):
            col = bcpd.ColorSpec(default="red")
        desc = Foo.__dict__["col"]
        f = Foo()
        assert f.col == "red"
        assert desc.get_value(f) == Value("red")
        f.col = "myfield"
        assert f.col == "myfield"
        assert desc.get_value(f) == Field("myfield")

    def test_default_tuple(self) -> None:
        class Foo(HasProps):
            col = bcpd.ColorSpec(default=(128, 255, 124))
        desc = Foo.__dict__["col"]
        f = Foo()
        assert f.col == (128, 255, 124)
        assert desc.get_value(f) == Value((128, 255, 124))

    def test_fixed_value(self) -> None:
        class Foo(HasProps):
            col = bcpd.ColorSpec("gray")
        desc = Foo.__dict__["col"]
        f = Foo()
        assert f.col == "gray"
        assert desc.get_value(f) == Value("gray")

    def test_named_value(self) -> None:
        class Foo(HasProps):
            col = bcpd.ColorSpec("colorfield")
        desc = Foo.__dict__["col"]
        f = Foo()

        f.col = "red"
        assert f.col == "red"
        assert desc.get_value(f) == Value("red")
        f.col = "forestgreen"
        assert f.col == "forestgreen"
        assert desc.get_value(f) == Value("forestgreen")

    def test_case_insensitive_named_value(self) -> None:
        class Foo(HasProps):
            col = bcpd.ColorSpec("colorfield")
        desc = Foo.__dict__["col"]
        f = Foo()

        f.col = "RED"
        assert f.col == "RED"
        assert desc.get_value(f) == Value("RED")
        f.col = "ForestGreen"
        assert f.col == "ForestGreen"
        assert desc.get_value(f) == Value("ForestGreen")

    def test_named_value_set_none(self) -> None:
        class Foo(HasProps):
            col = bcpd.ColorSpec("colorfield")
        desc = Foo.__dict__["col"]
        f = Foo()
        f.col = None
        assert desc.get_value(f) == Value(None)

    def test_named_value_unset(self) -> None:
        class Foo(HasProps):
            col = bcpd.ColorSpec("colorfield")
        desc = Foo.__dict__["col"]
        f = Foo()
        assert desc.get_value(f) == Field("colorfield")

    def test_named_color_overriding_default(self) -> None:
        class Foo(HasProps):
            col = bcpd.ColorSpec("colorfield")
        desc = Foo.__dict__["col"]
        f = Foo()
        f.col = "forestgreen"
        assert f.col == "forestgreen"
        assert desc.get_value(f) == Value("forestgreen")
        f.col = "myfield"
        assert f.col == "myfield"
        assert desc.get_value(f) == Field("myfield")

    def test_hex_value(self) -> None:
        class Foo(HasProps):
            col = bcpd.ColorSpec("colorfield")
        desc = Foo.__dict__["col"]
        f = Foo()
        f.col = "#FF004A"
        assert f.col == "#FF004A"
        assert desc.get_value(f) == Value("#FF004A")
        f.col = "myfield"
        assert f.col == "myfield"
        assert desc.get_value(f) == Field("myfield")

    def test_tuple_value(self) -> None:
        class Foo(HasProps):
            col = bcpd.ColorSpec("colorfield")
        desc = Foo.__dict__["col"]
        f = Foo()
        f.col = (128, 200, 255)
        assert f.col == (128, 200, 255)
        assert desc.get_value(f) == Value((128, 200, 255))
        f.col = "myfield"
        assert f.col == "myfield"
        assert desc.get_value(f) == Field("myfield")
        f.col = (100, 150, 200, 0.5)
        assert f.col == (100, 150, 200, 0.5)
        assert desc.get_value(f) == Value((100, 150, 200, 0.5))

    def test_set_dict(self) -> None:
        class Foo(HasProps):
            col = bcpd.ColorSpec("colorfield")
        desc = Foo.__dict__["col"]
        f = Foo()
        f.col = {"field": "myfield"}
        assert f.col == field("myfield")

        f.col = "field2"
        assert f.col == "field2"
        assert desc.get_value(f) == Field("field2")

    def test_isconst(self) -> None:
        assert bcpd.ColorSpec.isconst("red")
        assert bcpd.ColorSpec.isconst("#ff1234")

        assert not bcpd.ColorSpec.isconst(None)
        assert not bcpd.ColorSpec.isconst(10)
        assert not bcpd.ColorSpec.isconst((1, 2, 3, 0.5))

    def test_is_color_tuple_shape(self) -> None:
        assert bcpd.ColorSpec.is_color_tuple_shape((1, 2, 3, 0.5))
        assert bcpd.ColorSpec.is_color_tuple_shape((1.0, 2, 3, 0.5))
        assert bcpd.ColorSpec.is_color_tuple_shape((1, 2.0, 3, 0.5))
        assert bcpd.ColorSpec.is_color_tuple_shape((1, 2, 3.0, 0.5))

        assert not bcpd.ColorSpec.is_color_tuple_shape("red")
        assert not bcpd.ColorSpec.is_color_tuple_shape("#ff1234")
        assert not bcpd.ColorSpec.is_color_tuple_shape(None)
        assert not bcpd.ColorSpec.is_color_tuple_shape(10)

class Test_DistanceSpec:
    def test_default_value(self) -> None:
        class Foo(HasProps):
            x = bcpd.DistanceSpec(default=14)

        a = Foo()

        assert a.x == 14
        assert a.x_units == 'data'

class Test_FontSizeSpec:
    def test_font_size_from_string(self) -> None:
        class Foo(HasProps):
            x = bcpd.FontSizeSpec(default="0px")

        css_units = "%|em|ex|ch|ic|rem|vw|vh|vi|vb|vmin|vmax|cm|mm|q|in|pc|pt|px"

        a = Foo()
        assert a.x == "0px"

        for unit in css_units.split("|"):

            v = f"10{unit}"
            a.x = v
            assert a.x == v
            assert a.lookup('x').get_value(a) == Value(v)

            v = f"10.2{unit}"
            a.x = v
            assert a.x == v
            assert a.lookup('x').get_value(a) == Value(v)

            f = f"_10{unit}"
            a.x = f
            assert a.x == f
            assert a.lookup('x').get_value(a) == Field(f)

            f = f"_10.2{unit}"
            a.x = f
            assert a.x == f
            assert a.lookup('x').get_value(a) == Field(f)

        for unit in css_units.upper().split("|"):
            v = f"10{unit}"
            a.x = v
            assert a.x == v
            assert a.lookup('x').get_value(a) == Value(v)

            v = f"10.2{unit}"
            a.x = v
            assert a.x == v
            assert a.lookup('x').get_value(a) == Value(v)

            f = f"_10{unit}"
            a.x = f
            assert a.x == f
            assert a.lookup('x').get_value(a) == Field(f)

            f = f"_10.2{unit}"
            a.x = f
            assert a.x == f
            assert a.lookup('x').get_value(a) == Field(f)

    def test_bad_font_size_values(self) -> None:
        class Foo(HasProps):
            x = bcpd.FontSizeSpec(default="0px")

        a = Foo()

        with pytest.raises(ValueError):
            a.x = "6"

        with pytest.raises(ValueError):
            a.x = 6

        with pytest.raises(ValueError):
            a.x = ""

    def test_fields(self) -> None:
        class Foo(HasProps):
            x = bcpd.FontSizeSpec(default="0px")

        a = Foo()

        a.x = "_120"
        assert a.x == "_120"

        a.x = dict(field="_120")
        assert a.x == field("_120")

        a.x = "foo"
        assert a.x == "foo"

        a.x = dict(field="foo")
        assert a.x == field("foo")


class Test_NumberSpec:
    def test_field(self) -> None:
        class Foo(HasProps):
            x = bcpd.NumberSpec("xfield")
        f = Foo()
        assert f.x == "xfield"
        assert Foo.__dict__["x"].get_value(f) == Field("xfield")
        f.x = "my_x"
        assert f.x == "my_x"
        assert Foo.__dict__["x"].get_value(f) == Field("my_x")

    def test_value(self) -> None:
        class Foo(HasProps):
            x = bcpd.NumberSpec("xfield")
        f = Foo()
        assert f.x == "xfield"
        f.x = 12
        assert f.x == 12
        assert Foo.__dict__["x"].get_value(f) == Value(12)
        f.x = 15
        assert f.x == 15
        assert Foo.__dict__["x"].get_value(f) == Value(15)
        f.x = dict(value=32)
        assert Foo.__dict__["x"].get_value(f) == Value(32)

    def tests_accepts_timedelta(self):
        with warnings.catch_warnings():
            warnings.simplefilter(action="ignore", category=BokehDeprecationWarning)

            class Foo(HasProps):
                dt = bcpd.NumberSpec("dt", accept_datetime=True)
                ndt = bcpd.NumberSpec("ndt", accept_datetime=False)

            f = Foo()

            # FYI Numpy erroneously raises an annoying warning about elementwise
            # comparison below because a timedelta is compared to a float.
            # https://github.com/numpy/numpy/issues/10095
            with warnings.catch_warnings():
                warnings.simplefilter(action='ignore', category=DeprecationWarning)

                f.dt = datetime.timedelta(3, 54)
                assert f.dt == 259254000.0

                # counts as number.Real out of the box
                f.dt = np.timedelta64(3000, "ms")
                assert f.dt == np.timedelta64(3000, "ms")

                f.ndt = datetime.timedelta(3, 54)
                assert f.ndt == 259254000.0

                # counts as number.Real out of the box
                f.ndt = np.timedelta64(3000, "ms")
                assert f.ndt == np.timedelta64(3000, "ms")

    def tests_accepts_timedelta_with_pandas(self):
        with warnings.catch_warnings():
            warnings.simplefilter(action="ignore", category=BokehDeprecationWarning)

            class Foo(HasProps):
                dt = bcpd.NumberSpec("dt", accept_datetime=True)
                ndt = bcpd.NumberSpec("ndt", accept_datetime=False)

            f = Foo()

            # counts as number.Real out of the box
            f.dt = pd.Timedelta("3000ms")
            assert f.dt == 3000.0

            f.ndt = pd.Timedelta("3000ms")
            assert f.ndt == 3000.0

    def test_accepts_datetime(self) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter(action="ignore", category=BokehDeprecationWarning)

            class Foo(HasProps):
                dt = bcpd.NumberSpec("dt", accept_datetime=True)
                ndt = bcpd.NumberSpec("ndt", accept_datetime=False)

            f = Foo()

            f.dt = datetime.datetime(2016, 5, 11)
            assert f.dt == 1462924800000.0

            f.dt = np.datetime64("2016-05-11")
            assert f.dt == 1462924800000.0

            f.dt = datetime.date(2016, 5, 11)
            assert f.dt == 1462924800000.0

            with pytest.raises(ValueError):
                f.ndt = datetime.datetime(2016, 5, 11)

            with pytest.raises(ValueError):
                f.ndt = datetime.date(2016, 5, 11)

            with pytest.raises(ValueError):
                f.ndt = np.datetime64("2016-05-11")

    def test_default(self) -> None:
        class Foo(HasProps):
            y = bcpd.NumberSpec(default=12)
        f = Foo()
        assert f.y == 12
        assert Foo.__dict__["y"].get_value(f) == Value(12)
        f.y = "y1"
        assert f.y == "y1"
        # Once we set a concrete value, the default is ignored, because it is unused
        f.y = 32
        assert f.y == 32
        assert Foo.__dict__["y"].get_value(f) == Value(32)

    def test_multiple_instances(self) -> None:
        class Foo(HasProps):
            x = bcpd.NumberSpec("xfield")

        a = Foo()
        b = Foo()
        a.x = 13
        b.x = 14
        assert a.x == 13
        assert b.x == 14
        assert Foo.__dict__["x"].get_value(a) == Value(13)
        assert Foo.__dict__["x"].get_value(b) == Value(14)
        b.x = {"field": "x3"}
        assert Foo.__dict__["x"].get_value(a) == Value(13)
        assert Foo.__dict__["x"].get_value(b) == Field("x3")

    def test_set_from_json_keeps_mode(self) -> None:
        class Foo(HasProps):
            x = bcpd.NumberSpec(default=-1)

        a = Foo()

        assert a.x == -1

        # set as a value
        a.x = 14
        assert a.x == 14
        # set_from_json keeps the previous dict-ness or lack thereof
        a.set_from_json('x', dict(value=16))
        assert a.x == 16
        # but regular assignment overwrites the previous dict-ness
        a.x = dict(value=17)
        assert a.x == value(17)

        # set as a field
        a.x = "bar"
        assert a.x == "bar"
        # set_from_json keeps the previous dict-ness or lack thereof
        a.set_from_json('x', dict(field="foo"))
        assert a.x == "foo"
        # but regular assignment overwrites the previous dict-ness
        a.x = dict(field="baz")
        assert a.x == field("baz")


class Test_UnitSpec:
    def test_strict_key_values(self) -> None:
        class FooSpatialUnits(HasProps):
            x = bcpd.DistanceSpec("x")
        f = FooSpatialUnits()
        f.x = dict(field="foo", units="screen")
        with pytest.raises(ValueError):
            f.x = dict(field="foo", units="junk", foo="crap")
        class FooAngleUnits(HasProps):
            x = bcpd.AngleSpec("x")
        f = FooAngleUnits()
        f.x = dict(field="foo", units="deg")
        with pytest.raises(ValueError):
            f.x = dict(field="foo", units="junk", foo="crap")


class Test_HatchPatternSpec:
    def test_field(self) -> None:
        class Foo(HasProps):
            col = bcpd.HatchPatternSpec("colorfield")
        desc = Foo.__dict__["col"]

        f = Foo()
        assert f.col == "colorfield"
        assert desc.get_value(f) == Field("colorfield")

        f.col = "myfield"
        assert f.col == "myfield"
        assert desc.get_value(f) == Field("myfield")

        f.col = "dot"
        assert f.col == "dot"
        assert desc.get_value(f) == Value("dot")

        f.col = "/"
        assert f.col == "/"
        assert desc.get_value(f) == Value("/")

#-----------------------------------------------------------------------------
# Dev API
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Private API
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Code
#-----------------------------------------------------------------------------

Test___all__ = verify_all(bcpd, ALL)
