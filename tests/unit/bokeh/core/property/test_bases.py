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
from typing import Any
from unittest.mock import MagicMock, patch

# External imports
import numpy as np
import pandas as pd

# Bokeh imports
from bokeh.core.has_props import HasProps
from tests.support.util.api import verify_all
from tests.support.util.types import Capture

# Module under test
import bokeh.core.property.bases as bcpb # isort:skip

#-----------------------------------------------------------------------------
# Setup
#-----------------------------------------------------------------------------

ALL = (
    'ContainerProperty',
    'PrimitiveProperty',
    'Property',
    'validation_on',
)

#-----------------------------------------------------------------------------
# General API
#-----------------------------------------------------------------------------

class TestProperty:
    @patch('bokeh.core.property.bases.Property.validate')
    def test_is_valid_supresses_validation_detail(self, mock_validate: MagicMock) -> None:
        p = bcpb.Property()
        p.is_valid(None)
        assert mock_validate.called
        assert mock_validate.call_args[0] == (None, False)

    def test_serialized_default(self) -> None:
        class NormalProp(bcpb.Property[Any]):
            pass

        class ReadonlyProp(bcpb.Property[Any]):
            _readonly = True

        class NotSerializedProp(bcpb.Property[Any]):
            _serialized = False

        p0 = NormalProp()
        assert p0.serialized is True
        assert p0.readonly is False

        p1 = ReadonlyProp()
        assert p1.serialized is False
        assert p1.readonly is True

        p2 = NotSerializedProp()
        assert p2.serialized is False
        assert p2.readonly is False

    def test_assert_bools(self) -> None:
        hp = HasProps()
        p = bcpb.Property()

        p.asserts(True, "true")
        assert p.prepare_value(hp, "foo", 10) == 10

        p.asserts(False, "false")
        with pytest.raises(ValueError) as e:
                p.prepare_value(hp, "foo", 10)
                assert str(e) == "false"

    def test_assert_functions(self) -> None:
        hp = HasProps()
        p = bcpb.Property()

        p.asserts(lambda obj, value: True, "true")
        p.asserts(lambda obj, value: obj is hp, "true")
        p.asserts(lambda obj, value: value==10, "true")
        assert p.prepare_value(hp, "foo", 10) == 10

        p.asserts(lambda obj, value: False, "false")
        with pytest.raises(ValueError) as e:
                p.prepare_value(hp, "foo", 10)
                assert str(e) == "false"

    def test_assert_msg_funcs(self) -> None:
        hp = HasProps()
        p = bcpb.Property()

        def raise_(ex):
                raise ex

        p.asserts(False, lambda obj, name, value: raise_(ValueError(f"bad {hp==obj} {name} {value}")))

        with pytest.raises(ValueError) as e:
                p.prepare_value(hp, "foo", 10)
                assert str(e) == "bad True name, 10"

    def test_matches_basic_types(self, capsys: Capture) -> None:
        p = bcpb.Property()
        for x in [1, 1.2, "a", np.arange(4), None, False, True, {}, []]:
                assert p.matches(x, x) is True
                assert p.matches(x, "junk") is False
        out, err = capsys.readouterr()
        assert err == ""

    def test_matches_compatible_arrays(self, capsys: Capture) -> None:
        p = bcpb.Property()
        a = np.arange(5)
        b = np.arange(5)
        assert p.matches(a, b) is True
        assert p.matches(a, b+1) is False
        for x in [1, 1.2, "a", np.arange(4), None, False]:
                assert p.matches(a, x) is False
                assert p.matches(x, b) is False
        out, err = capsys.readouterr()
        assert err == ""

    def test_matches_incompatible_arrays(self, capsys: Capture) -> None:
        p = bcpb.Property()
        a = np.arange(5)
        b = np.arange(5).astype(str)
        assert p.matches(a, b) is False
        out, err = capsys.readouterr()
        # no way to suppress FutureWarning in this case
        # assert err == ""

    def test_matches_dicts_with_array_values(self, capsys: Capture) -> None:
        p = bcpb.Property()
        d1 = dict(foo=np.arange(10))
        d2 = dict(foo=np.arange(10))

        assert p.matches(d1, d1) is True
        assert p.matches(d1, d2) is True

        # XXX not sure if this is preferable to have match, or not
        assert p.matches(d1, dict(foo=list(range(10)))) is True

        assert p.matches(d1, dict(foo=np.arange(11))) is False
        assert p.matches(d1, dict(bar=np.arange(10))) is False
        assert p.matches(d1, dict(bar=10)) is False
        out, err = capsys.readouterr()
        assert err == ""

    def test_matches_non_dict_containers_with_array_false(self, capsys: Capture) -> None:
        p = bcpb.Property()
        d1 = [np.arange(10)]
        d2 = [np.arange(10)]
        assert p.matches(d1, d1) is True  # because object identity
        assert p.matches(d1, d2) is False

        t1 = (np.arange(10),)
        t2 = (np.arange(10),)
        assert p.matches(t1, t1) is True  # because object identity
        assert p.matches(t1, t2) is False

        out, err = capsys.readouterr()
        assert err == ""

    def test_matches_dicts_with_series_values(self, capsys: Capture) -> None:
        p = bcpb.Property()
        d1 = pd.DataFrame(dict(foo=np.arange(10)))
        d2 = pd.DataFrame(dict(foo=np.arange(10)))

        assert p.matches(d1.foo, d1.foo) is True
        assert p.matches(d1.foo, d2.foo) is True

        # XXX not sure if this is preferable to have match, or not
        assert p.matches(d1.foo, (range(10))) is True

        assert p.matches(d1.foo, np.arange(11)) is False
        assert p.matches(d1.foo, np.arange(10)+1) is False
        assert p.matches(d1.foo, 10) is False
        out, err = capsys.readouterr()
        assert err == ""

    def test_matches_dicts_with_index_values(self, capsys: Capture) -> None:
        p = bcpb.Property()
        d1 = pd.DataFrame(dict(foo=np.arange(10)))
        d2 = pd.DataFrame(dict(foo=np.arange(10)))

        assert p.matches(d1.index, d1.index) is True
        assert p.matches(d1.index, d2.index) is True

        # XXX not sure if this is preferable to have match, or not
        assert p.matches(d1.index, list(range(10))) is True

        assert p.matches(d1.index, np.arange(11)) is False
        assert p.matches(d1.index, np.arange(10)+1) is False
        assert p.matches(d1.index, 10) is False
        out, err = capsys.readouterr()
        assert err == ""

    def test_validation_on(self) -> None:
        assert bcpb.Property._should_validate is True
        assert bcpb.validation_on()

        bcpb.Property._should_validate = False
        assert not bcpb.validation_on()

        bcpb.Property._should_validate = True
        assert bcpb.validation_on()

    def test__hinted_value_is_identity(self) -> None:
        p = bcpb.Property()
        assert p._hinted_value(10, "hint") == 10
        assert p._hinted_value(10, None) == 10

    @patch('bokeh.core.property.bases.Property._hinted_value')
    def test_prepare_value_uses__hinted_value(self, mock_hv: MagicMock) -> None:
        hp = HasProps()
        p = bcpb.Property()

        p.prepare_value(hp, "foo", 10)
        assert mock_hv.called

    def test_pandas_na(self):
        # Property.matches handles this as False could change in the future.
        # pd.NA raises a TypeError when bool(pd.NA == pd.NA)
        assert bcpb.Property().matches(pd.NA, pd.NA) is False
        assert bcpb.Property().matches({"name": pd.NA}, {"name": 1}) is False

    def test_nan(self):
        # Property.matches handles this as False could change in the future.
        assert bcpb.Property().matches(np.nan, np.nan) is False
        assert bcpb.Property().matches({"name": np.nan}, {"name": np.nan}) is False
        assert bcpb.Property().matches(np.array([np.nan]), np.array([np.nan])) is False

    def test_nat(self):
        # Property.matches handles this as False could change in the future.
        nat = np.datetime64("NAT")
        assert np.isnat(nat)
        assert bcpb.Property().matches(nat, nat) is False
        assert bcpb.Property().matches({"name": nat}, {"name": nat}) is False
        assert bcpb.Property().matches(np.array([nat]), np.array([nat])) is False

#-----------------------------------------------------------------------------
# Dev API
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Private API
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Code
#-----------------------------------------------------------------------------

Test___all__ = verify_all(bcpb, ALL)
