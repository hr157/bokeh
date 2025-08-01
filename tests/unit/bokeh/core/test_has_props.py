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
from types import MethodType
from unittest.mock import MagicMock, patch

# Bokeh imports
from bokeh.core.properties import (
    Alias,
    AngleSpec,
    Either,
    Instance,
    Int,
    List,
    Nullable,
    NumberSpec,
    Override,
    Required,
    String,
)
from bokeh.core.property.descriptors import (
    DataSpecPropertyDescriptor,
    PropertyDescriptor,
    UnsetValueError,
)
from bokeh.core.property.singletons import Intrinsic, Undefined
from bokeh.core.property.vectorization import field, value
from bokeh.util.warnings import BokehUserWarning

# Module under test
import bokeh.core.has_props as hp # isort:skip

#-----------------------------------------------------------------------------
# Setup
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# General API
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Dev API
#-----------------------------------------------------------------------------

class Parent(hp.HasProps):
    int1 = Int(default=10)
    ds1 = NumberSpec(default=field("x"))
    lst1 = List(String)

    @property
    def foo_prop(self) -> int:
        return 110

    def foo_func(self) -> int:
        return 111

    @property
    def _foo_prop(self) -> int:
        return 1100

    def _foo_func(self) -> int:
        return 1110

class Child(Parent):
    int2 = Nullable(Int())
    str2 = String(default="foo")
    ds2 = NumberSpec(default=field("y"))
    lst2 = List(Int, default=[1,2,3])

    @property
    def str2_proxy(self):
        return self.str2
    @str2_proxy.setter
    def str2_proxy(self, value):
        self.str2 = value*2

class OverrideChild(Parent):
    int1 = Override(default=20)

class AliasedChild(Child):
    aliased_int1 = Alias("int1")
    aliased_int2 = Alias("int2")

def test_HasProps_getattr() -> None:
    p = Parent()

    assert getattr(p, "int1") == 10
    assert p.int1 == 10

    assert getattr(p, "foo_prop") == 110
    assert p.foo_prop == 110

    assert isinstance(getattr(p, "foo_func"), MethodType)
    assert isinstance(p.foo_func, MethodType)

    assert getattr(p, "foo_func")() == 111
    assert p.foo_func() == 111

    assert getattr(p, "_foo_prop") == 1100
    assert p._foo_prop == 1100

    assert isinstance(getattr(p, "_foo_func"), MethodType)
    assert isinstance(p._foo_func, MethodType)

    assert getattr(p, "_foo_func")() == 1110
    assert p._foo_func() == 1110

    with pytest.raises(AttributeError):
        getattr(p, "foo_prop2")
    with pytest.raises(AttributeError):
        p.foo_prop2

    with pytest.raises(AttributeError):
        getattr(p, "foo_func2")
    with pytest.raises(AttributeError):
        p.foo_func2

    with pytest.raises(AttributeError):
        getattr(p, "_foo_prop2")
    with pytest.raises(AttributeError):
        p._foo_prop2

    with pytest.raises(AttributeError):
        getattr(p, "_foo_func2")
    with pytest.raises(AttributeError):
        p._foo_func2

def test_HasProps_default_init() -> None:
    p = Parent()
    assert p.int1 == 10
    assert p.ds1 == field("x")
    assert p.lst1 == []

    c = Child()
    assert c.int1 == 10
    assert c.ds1 == field("x")
    assert c.lst1 == []
    assert c.int2 is None
    assert c.str2 == "foo"
    assert c.ds2 == field("y")
    assert c.lst2 == [1,2,3]

def test_HasProps_kw_init() -> None:
    p = Parent(int1=30, ds1=field("foo"))
    assert p.int1 == 30
    assert p.ds1 == field("foo")
    assert p.lst1 == []

    c = Child(str2="bar", lst2=[2,3,4], ds2=10)
    assert c.int1 == 10
    assert c.ds1 == field("x")
    assert c.lst1 == []
    assert c.int2 is None
    assert c.str2 == "bar"
    assert c.ds2 == 10
    assert c.lst2 == [2,3,4]

def test_HasProps_override() -> None:
    ov = OverrideChild()
    assert ov.int1 == 20
    assert ov.ds1 == field("x")
    assert ov.lst1 == []

def test_HasProps_intrinsic() -> None:
    obj0 = Parent(int1=Intrinsic, ds1=Intrinsic, lst1=Intrinsic)

    assert obj0.int1 == 10
    assert obj0.ds1 == field("x")
    assert obj0.lst1 == []

    obj1 = Parent(int1=30, ds1=field("y"), lst1=["x", "y", "z"])

    assert obj1.int1 == 30
    assert obj1.ds1 == field("y")
    assert obj1.lst1 == ["x", "y", "z"]

    obj1.int1 = Intrinsic
    obj1.ds1 = Intrinsic
    obj1.lst1 = Intrinsic

    assert obj1.int1 == 10
    assert obj1.ds1 == field("x")
    assert obj1.lst1 == []

def test_HasProps_alias() -> None:
    obj0 = AliasedChild()
    assert obj0.int1 == 10
    assert obj0.int2 is None
    assert obj0.aliased_int1 == 10
    assert obj0.aliased_int2 is None
    obj0.int1 = 20
    assert obj0.int1 == 20
    assert obj0.int2 is None
    assert obj0.aliased_int1 == 20
    assert obj0.aliased_int2 is None
    obj0.int2 = 1
    assert obj0.int1 == 20
    assert obj0.int2 == 1
    assert obj0.aliased_int1 == 20
    assert obj0.aliased_int2 == 1
    obj0.aliased_int1 = 30
    assert obj0.int1 == 30
    assert obj0.int2 == 1
    assert obj0.aliased_int1 == 30
    assert obj0.aliased_int2 == 1
    obj0.aliased_int2 = 2
    assert obj0.int1 == 30
    assert obj0.int2 == 2
    assert obj0.aliased_int1 == 30
    assert obj0.aliased_int2 == 2

    obj1 = AliasedChild(int1=20)
    assert obj1.int1 == 20
    assert obj1.int2 is None
    assert obj1.aliased_int1 == 20
    assert obj1.aliased_int2 is None

    obj2 = AliasedChild(int2=1)
    assert obj2.int1 == 10
    assert obj2.int2 == 1
    assert obj2.aliased_int1 == 10
    assert obj2.aliased_int2 == 1

    obj3 = AliasedChild(int1=20, int2=1)
    assert obj3.int1 == 20
    assert obj3.int2 == 1
    assert obj3.aliased_int1 == 20
    assert obj3.aliased_int2 == 1

    obj4 = AliasedChild(aliased_int1=20)
    assert obj4.int1 == 20
    assert obj4.int2 is None
    assert obj4.aliased_int1 == 20
    assert obj4.aliased_int2 is None

    obj5 = AliasedChild(aliased_int2=1)
    assert obj5.int1 == 10
    assert obj5.int2 == 1
    assert obj5.aliased_int1 == 10
    assert obj5.aliased_int2 == 1

    obj6 = AliasedChild(aliased_int1=20, aliased_int2=1)
    assert obj6.int1 == 20
    assert obj6.int2 == 1
    assert obj6.aliased_int1 == 20
    assert obj6.aliased_int2 == 1

def test_HasProps_equals() -> None:
    p1 = Parent()
    p2 = Parent()
    assert p1.equals(p2)
    p1.int1 = 25
    assert not p1.equals(p2)
    p2.int1 = 25
    assert p1.equals(p2)

def test_HasProps_update() -> None:
    c = Child()
    c.update(**dict(lst2=[1,2], str2="baz", int1=25, ds1=value(123)))
    assert c.int1 == 25
    assert c.ds1 == value(123)
    assert c.lst1 == []
    assert c.int2 is None
    assert c.str2 == "baz"
    assert c.ds2 == field("y")
    assert c.lst2 == [1,2]

def test_HasProps_set_from_json() -> None:
    c = Child()
    c.set_from_json('lst2', [1,2])
    assert c.int1 == 10
    assert c.ds1 == field("x")
    assert c.lst1 == []
    assert c.int2 is None
    assert c.str2 == "foo"
    assert c.ds2 == field("y")
    assert c.lst2 == [1,2]

    c.set_from_json('ds1', "foo")
    assert c.int1 == 10
    assert c.ds1 == "foo"
    assert c.lst1 == []
    assert c.int2 is None
    assert c.str2 == "foo"
    assert c.ds2 == field("y")
    assert c.lst2 == [1,2]

    c.set_from_json('int2', 100)
    assert c.int1 == 10
    assert c.ds1 == "foo"
    assert c.lst1 == []
    assert c.int2 == 100
    assert c.str2 == "foo"
    assert c.ds2 == field("y")
    assert c.lst2 == [1,2]


def test_HasProps_set() -> None:
    c = Child()
    c.update(**dict(lst2=[1,2], str2="baz", int1=25, ds1=field("foo")))
    assert c.int1 == 25
    assert c.ds1 == field("foo")
    assert c.lst1 == []
    assert c.int2 is None
    assert c.str2 == "baz"
    assert c.ds2 == field("y")
    assert c.lst2 == [1,2]

    c.str2_proxy = "some"
    assert c.str2 == "somesome"
    assert c.str2_proxy == "somesome"

def test_HasProps_set_error() -> None:
    c = Child()
    with pytest.raises(AttributeError) as e:
        c.int3 = 10
    assert str(e.value).endswith("unexpected attribute 'int3' to Child, similar attributes are int2 or int1")
    with pytest.raises(AttributeError) as e:
        c.junkjunk = 10
    assert str(e.value).endswith("unexpected attribute 'junkjunk' to Child, possible attributes are ds1, ds2, int1, int2, lst1, lst2 or str2")


def test_HasProps_lookup() -> None:
    p = Parent()
    d = p.lookup('int1')
    assert isinstance(d, PropertyDescriptor)
    assert d.name == 'int1'
    d = p.lookup('ds1')
    assert isinstance(d, DataSpecPropertyDescriptor)
    assert d.name == 'ds1'
    d = p.lookup('lst1')
    assert isinstance(d, PropertyDescriptor)
    assert d.name == 'lst1'

def test_HasProps_apply_theme() -> None:
    c = Child()
    theme = dict(int2=10, lst1=["foo", "bar"])
    c.apply_theme(theme)
    assert c.themed_values() is theme
    c.apply_theme(theme)
    assert c.themed_values() is theme

    assert c.int2 == 10
    assert c.lst1 == ["foo", "bar"]

    assert c.int1 == 10
    assert c.ds1 == field("x")
    assert c.str2 == "foo"
    assert c.ds2 == field("y")
    assert c.lst2 == [1,2,3]

    c.int2 = 25
    assert c.int2 == 25
    assert c.lst1 == ["foo", "bar"]

    assert c.int1 == 10
    assert c.ds1 == field("x")
    assert c.str2 == "foo"
    assert c.ds2 == field("y")
    assert c.lst2 == [1,2,3]

    c.ds2 = "foo"
    assert c.int2 == 25
    assert c.lst1 == ["foo", "bar"]

    assert c.int1 == 10
    assert c.ds1 == field("x")
    assert c.str2 == "foo"
    assert c.ds2 == "foo"
    assert c.lst2 == [1,2,3]

def test_HasProps_unapply_theme() -> None:
    c = Child()
    theme = dict(int2=10, lst1=["foo", "bar"])
    c.apply_theme(theme)
    assert c.int2 == 10
    assert c.lst1 == ["foo", "bar"]

    assert c.int1 == 10
    assert c.ds1 == field("x")
    assert c.str2 == "foo"
    assert c.ds2 == field("y")
    assert c.lst2 == [1,2,3]

    c.unapply_theme()
    assert c.int2 is None
    assert c.lst1 == []

    assert c.int1 == 10
    assert c.ds1 == field("x")
    assert c.str2 == "foo"
    assert c.ds2 == field("y")
    assert c.lst2 == [1,2,3]

    assert c.themed_values() is None

class EitherSimpleDefault(hp.HasProps):
    foo = Either(List(Int), Int, default=10)

def test_HasProps_apply_theme_either_simple() -> None:

    # check applying multiple themes
    c = EitherSimpleDefault()
    assert c.foo == 10

    theme = dict(foo=20)
    c.apply_theme(theme)
    assert c.foo == 20

    theme = dict(foo=30)
    c.apply_theme(theme)
    assert c.foo == 30

    # check user set before theme
    c = EitherSimpleDefault()
    theme = dict(foo=30)
    c.foo = 50
    c.apply_theme(theme)
    assert c.foo == 50

    # check user set after theme
    c = EitherSimpleDefault()
    theme = dict(foo=30)
    c.apply_theme(theme)
    c.foo = 50
    assert c.foo == 50

    # check user set alt type
    c = EitherSimpleDefault()
    theme = dict(foo=30)
    c.foo = [50]
    c.apply_theme(theme)
    assert c.foo == [50]

    # check themed alt type
    c = EitherSimpleDefault()
    theme = dict(foo=[100])
    c.apply_theme(theme)
    assert c.foo == [100]

class EitherContainerDefault(hp.HasProps):
    foo = Either(List(Int), Int, default=[10])

def test_HasProps_apply_theme_either_container() -> None:

    # check applying multiple themes
    c = EitherContainerDefault()
    assert c.foo == [10]

    theme = dict(foo=[20])
    c.apply_theme(theme)
    assert c.foo == [20]

    theme = dict(foo=[30])
    c.apply_theme(theme)
    assert c.foo == [30]

    # check user set before theme
    c = EitherContainerDefault()
    theme = dict(foo=[30])
    c.foo = [50]
    c.apply_theme(theme)
    assert c.foo == [50]

    # check user set after theme
    c = EitherContainerDefault()
    theme = dict(foo=[30])
    c.apply_theme(theme)
    c.foo = [50]
    assert c.foo == [50]

    # check user set alt type
    c = EitherContainerDefault()
    theme = dict(foo=[30])
    c.foo = 50
    c.apply_theme(theme)
    assert c.foo == 50

    # check themed alt type
    c = EitherContainerDefault()
    theme = dict(foo=100)
    c.apply_theme(theme)
    assert c.foo == 100

class IntFuncDefault(hp.HasProps):
    foo = Int(default=lambda: 10)

def test_HasProps_apply_theme_func_default() -> None:

    # check applying multiple themes
    c = IntFuncDefault()
    assert c.foo == 10

    theme = dict(foo=20)
    c.apply_theme(theme)
    assert c.foo == 20

    theme = dict(foo=30)
    c.apply_theme(theme)
    assert c.foo == 30

    # check user set before theme
    c = IntFuncDefault()
    theme = dict(foo=30)
    c.foo = 50
    c.apply_theme(theme)
    assert c.foo == 50

    # check user set after theme
    c = IntFuncDefault()
    theme = dict(foo=30)
    c.apply_theme(theme)
    c.foo = 50
    assert c.foo == 50

def test_has_props_dupe_prop() -> None:
    try:
        class DupeProps(hp.HasProps):
            bar = AngleSpec()
            bar_units = String()
    except RuntimeError as e:
        assert str(e) == "Two property generators both created DupeProps.bar_units"
    else:
        assert False

class TopLevelQualified(hp.HasProps, hp.Qualified):
    foo = Int()

class TopLevelNonQualified(hp.HasProps, hp.NonQualified):
    foo = Int()

def test_qualified() -> None:
    class InnerQualified(hp.HasProps, hp.Qualified):
        foo = Int()

    class InnerNonQualified(hp.HasProps, hp.NonQualified):
        foo = Int()

    assert TopLevelQualified.__qualified_model__ == "test_has_props.TopLevelQualified"
    assert TopLevelNonQualified.__qualified_model__ == "TopLevelNonQualified"
    assert InnerQualified.__qualified_model__ == "test_has_props.test_qualified.InnerQualified"
    assert InnerNonQualified.__qualified_model__ == "test_qualified.InnerNonQualified"

class Some0HasProps(hp.HasProps, hp.Local):
    f0 = Int(default=3)
    f1 = List(Int, default=[3, 4, 5])

class Some1HasProps(hp.HasProps, hp.Local):
    f0 = String(default="xyz")
    f1 = List(String, default=["x", "y", "z"])

class Some2HasProps(hp.HasProps, hp.Local):
    f0 = Instance(Some0HasProps, lambda: Some0HasProps())
    f1 = Instance(Some1HasProps, lambda: Some1HasProps())
    f2 = Int(default=1)
    f3 = String(default="xyz")
    f4 = List(Int, default=[1, 2, 3])

class Some3HasProps(hp.HasProps, hp.Local):
    f4 = Int(default=4)
    f3 = Int(default=3)
    f2 = Int(default=2)
    f1 = Int(default=1)

class Some4HasProps(hp.HasProps, hp.Local):
    f0 = Required(Int)
    f1 = Int()
    f2 = Int(default=1)

def test_HasProps_properties_with_values_maintains_order() -> None:
    v0 = Some3HasProps()
    assert list(v0.properties_with_values(include_defaults=False).items()) == []
    assert list(v0.properties_with_values(include_defaults=True).items()) == [("f4", 4), ("f3", 3), ("f2", 2), ("f1", 1)]

    v1 = Some3HasProps(f1=10, f4=40)
    assert list(v1.properties_with_values(include_defaults=False).items()) == [("f4", 40), ("f1", 10)]
    assert list(v1.properties_with_values(include_defaults=True).items()) == [("f4", 40), ("f3", 3), ("f2", 2), ("f1", 10)]

    v2 = Some3HasProps(f4=40, f1=10)
    assert list(v2.properties_with_values(include_defaults=False).items()) == [("f4", 40), ("f1", 10)]
    assert list(v2.properties_with_values(include_defaults=True) .items()) == [("f4", 40), ("f3", 3), ("f2", 2), ("f1", 10)]

def test_HasProps_properties_with_values_unstable() -> None:
    v0 = Some0HasProps()
    assert v0.properties_with_values(include_defaults=False) == {}

    v1 = Some1HasProps()
    assert v1.properties_with_values(include_defaults=False) == {}

    v2 = Some2HasProps()
    assert v2.properties_with_values(include_defaults=False) == {"f0": v2.f0, "f1": v2.f1}

def test_HasProps_properties_with_values_unset() -> None:
    v0 = Some4HasProps()

    with pytest.raises(UnsetValueError):
        v0.properties_with_values(include_defaults=False, include_undefined=False)
    with pytest.raises(UnsetValueError):
        v0.properties_with_values(include_defaults=True, include_undefined=False)
    assert v0.properties_with_values(include_defaults=False, include_undefined=True) == {"f0": Undefined}
    assert v0.properties_with_values(include_defaults=True, include_undefined=True) == {"f0": Undefined, "f1": 0, "f2": 1}

    v1 = Some4HasProps(f0=10)

    assert v1.properties_with_values(include_defaults=False, include_undefined=False) == {"f0": 10}
    assert v1.properties_with_values(include_defaults=True, include_undefined=False) == {"f0": 10, "f1": 0, "f2": 1}
    assert v1.properties_with_values(include_defaults=False, include_undefined=True) == {"f0": 10}
    assert v1.properties_with_values(include_defaults=True, include_undefined=True) == {"f0": 10, "f1": 0, "f2": 1}

def test_HasProps_descriptors() -> None:
    v0 = Some0HasProps()

    d0 = v0.descriptors()
    assert len(d0) == 2
    assert d0[0].name == "f0"
    assert d0[1].name == "f1"

    v1 = Some1HasProps()

    d1 = v1.descriptors()
    assert len(d1) == 2
    assert d1[0].name == "f0"
    assert d1[1].name == "f1"

    v2 = Some2HasProps()

    d2 = v2.descriptors()
    assert len(d2) == 5
    assert d2[0].name == "f0"
    assert d2[1].name == "f1"
    assert d2[2].name == "f2"
    assert d2[3].name == "f3"
    assert d2[4].name == "f4"

def test_HasProps_abstract() -> None:
    @hp.abstract
    class Base(hp.HasProps, hp.Local):
        pass

    class Derived(Base):
        pass

    assert hp.is_abstract(Base) is True
    assert hp.is_abstract(Derived) is False

def test_HasProps_clone() -> None:
    obj0 = Some0HasProps()
    obj1 = Some1HasProps()
    obj2 = Some2HasProps(
        f0=obj0,
        f1=obj1,
        f2=2,
        f3="uvw",
        f4=[7, 8, 9],
    )

    obj3 = obj2.clone()
    assert obj3 is not obj2
    assert obj3.f0 is obj0
    assert obj3.f1 is obj1
    assert obj3.f2 == 2
    assert obj3.f3 == "uvw"
    assert obj3.f4 is obj2.f4

def test_HasProps_clone_with_overrides() -> None:
    obj0 = Some0HasProps()
    obj1 = Some1HasProps()
    obj2 = Some2HasProps(
        f0=obj0,
        f1=obj1,
        f2=2,
        f3="uvw",
        f4=[7, 8, 9],
    )

    obj3 = obj2.clone(f2=3)
    assert obj3 is not obj2
    assert obj3.f0 is obj0
    assert obj3.f1 is obj1
    assert obj3.f2 == 3
    assert obj3.f3 == "uvw"
    assert obj3.f4 is obj2.f4

def test_HasProps_clone_with_unset_properties() -> None:
    obj0 = Some4HasProps(f1=1, f2=2)
    obj1 = obj0.clone()

    assert obj1 is not obj0
    assert obj1.properties_with_values(include_defaults=False, include_undefined=True) == dict(f0=Undefined, f1=1, f2=2)

@patch("warnings.warn")
def test_HasProps_model_redefinition(mock_warn: MagicMock) -> None:
    class Foo1(hp.HasProps):
        __qualified_model__ = "Foo"

    class Foo2(hp.HasProps):
        __qualified_model__ = "Foo"

    assert mock_warn.called

    msg, cls = mock_warn.call_args[0]
    assert msg.startswith("Duplicate qualified model definition of 'Foo'.")
    assert cls is BokehUserWarning

#-----------------------------------------------------------------------------
# Private API
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Code
#-----------------------------------------------------------------------------
