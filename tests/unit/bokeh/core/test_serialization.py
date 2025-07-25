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
import datetime as dt
import gzip
import sys
from array import array as TypedArray
from base64 import b64decode
from math import inf, nan
from types import SimpleNamespace
from typing import Any, Sequence
from unittest.mock import patch

# External imports
import numpy as np
import pandas as pd

# Bokeh imports
from bokeh.colors import RGB
from bokeh.core.has_props import HasProps
from bokeh.core.properties import (
    Instance,
    Int,
    List,
    Nullable,
    Required,
    String,
)
from bokeh.core.property.descriptors import UnsetValueError
from bokeh.core.property.wrappers import PropertyValueColumnData
from bokeh.core.serialization import (
    Buffer,
    BytesRep,
    DeserializationError,
    Deserializer,
    MapRep,
    NDArrayRep,
    NumberRep,
    ObjectRefRep,
    ObjectRep,
    Ref,
    SerializationError,
    Serializer,
    SetRep,
    SliceRep,
    TypedArrayRep,
)
from bokeh.model import Model
from bokeh.util.dataclasses import NotRequired, Unspecified, dataclass
from bokeh.util.warnings import BokehUserWarning

#-----------------------------------------------------------------------------
# Setup
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# General API
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Dev API
#-----------------------------------------------------------------------------

class SomeProps(HasProps):
    p0 = Int(default=1)
    p1 = String()
    p2 = List(Int)

class SomeModel(Model):
    p0 = Int(default=1)
    p1 = String()
    p2 = List(Int)
    p3 = Nullable(Instance(lambda: SomeModel))

class SomeModelUnset(SomeModel):
    p4 = Required(Int)

@dataclass
class SomeDataClass:
    f0: int
    f1: Sequence[int]
    f2: SomeDataClass | None = None
    f3: NotRequired[bool | None] = Unspecified
    f4: NotRequired[SomeProps] = Unspecified
    f5: NotRequired[SomeModel] = Unspecified

class TestBuffer:

    def test_ref(self) -> None:
        buf = Buffer(10, b"\x001\xefabc\x12")
        assert buf.ref == {'id': 10}

    def test_to_bytes_from_bytes(self) -> None:
        val = b"\x001\xefabc\x12"
        buf = Buffer(10, val)
        ret = buf.to_bytes()
        assert isinstance(ret, bytes)
        assert ret == val

    def test_to_bytes_from_memoryview(self) -> None:
        val = b"\x001\xefabc\x12"
        view = memoryview(val)
        buf = Buffer(10, view)
        ret = buf.to_bytes()
        assert isinstance(ret, bytes)
        assert ret == val

    def test_to_compressed_bytes_from_bytes(self) -> None:
        val = b"\x001\xefabc\x12"
        buf = Buffer(10, val)

        ret = buf.to_compressed_bytes()

        assert isinstance(ret, bytes)

        # make sure the gzip header "OS" field is *always* set to "unknown" (255)
        assert ret[9] == 255

        assert gzip.decompress(ret) == val

    def test_to_compressed_bytes_from_memoryview(self) -> None:
        val = b"\x001\xefabc\x12"
        view = memoryview(val)
        buf = Buffer(10, view)

        ret = buf.to_compressed_bytes()

        assert isinstance(ret, bytes)

        # make sure the gzip header "OS" field is *always* set to "unknown" (255)
        assert ret[9] == 255

        assert gzip.decompress(ret) == val

    @pytest.mark.parametrize("level", range(0, 10))
    @patch("gzip.compress")
    def test_to_compressed_compression_level(self, compress, level: int, monkeypatch: pytest.MonkeyPatch) -> None:
        val = b"\x001\xefabc\x12"
        buf = Buffer(10, val)

        monkeypatch.setenv("BOKEH_COMPRESSION_LEVEL", f"{level}")
        buf.to_compressed_bytes()

        compress.assert_called_once_with(val, mtime=1, compresslevel=level)

    def test_to_base64(self):
        val = b"\x001\xefabc\x12"
        buf = Buffer(10, val)

        ret = buf.to_base64()

        assert isinstance(ret, str)
        assert b64decode(ret) == buf.to_compressed_bytes()

class TestSerializer:

    def test_primitive(self) -> None:
        encoder = Serializer()

        assert encoder.encode(None) is None
        assert encoder.encode(False) is False
        assert encoder.encode(True) is True
        assert encoder.encode("abc") == "abc"

        assert encoder.encode(1) == 1
        assert encoder.encode(1.17) == 1.17

        assert encoder.encode(nan) == NumberRep(type="number", value="nan")

        assert encoder.encode(-inf) == NumberRep(type="number", value="-inf")
        assert encoder.encode(+inf) == NumberRep(type="number", value="+inf")

        assert encoder.buffers == []

    def test_non_serializable(self):
        encoder = Serializer()

        with pytest.raises(SerializationError):
            encoder.encode(property())

        with pytest.raises(SerializationError):
            encoder.encode(range(0, 10))

    def test_max_int(self) -> None:
        encoder = Serializer()

        with pytest.warns(BokehUserWarning, match="out of range integer may result in loss of precision"):
            rep = encoder.encode(2**64)

        assert rep == 2.0**64
        assert isinstance(rep, float)

    def test_list_empty(self) -> None:
        val = []

        encoder = Serializer()
        rep = encoder.encode(val)

        assert rep == []
        assert encoder.buffers == []

    def test_list(self) -> None:
        v0 = SomeProps(p0=2, p1="a", p2=[1, 2, 3])
        v1 = SomeModel(p0=3, p1="b", p2=[4, 5, 6])
        v2 = SomeDataClass(f0=2, f1=[1, 2, 3])

        val = [None, False, True, "abc", 1, 1.17, nan, -inf, +inf, v0, v1, v2, [nan]]

        encoder = Serializer()
        rep = encoder.encode(val)
        assert rep == [
            None, False, True, "abc", 1, 1.17,
            NumberRep(type="number", value="nan"),
            NumberRep(type="number", value="-inf"),
            NumberRep(type="number", value="+inf"),
            ObjectRep(
                type="object",
                name="test_serialization.SomeProps",
                attributes=dict(
                    p0=2,
                    p1="a",
                    p2=[1, 2, 3],
                ),
            ),
            ObjectRefRep(
                type="object",
                name="test_serialization.SomeModel",
                id=v1.id,
                attributes=dict(
                    p0=3,
                    p1="b",
                    p2=[4, 5, 6],
                ),
            ),
            ObjectRep(
                type="object",
                name="test_serialization.SomeDataClass",
                attributes=dict(
                    f0=2,
                    f1=[1, 2, 3],
                    f2=None,
                ),
            ),
            [NumberRep(type="number", value="nan")],
        ]
        assert encoder.buffers == []

    def test_list_circular_with_checking(self) -> None:
        val: Sequence[Any] = [1, 2, 3]
        val.append(val)

        encoder = Serializer(check_circular=True)
        with pytest.raises(SerializationError, match="circular reference"):
            encoder.encode(val)

    @pytest.mark.skipif(sys.platform == "win32" and sys.version_info < (3, 11), reason="stack overflow instead of RecursionError")
    def test_list_circular_without_checking(self) -> None:
        val: Sequence[Any] = [1, 2, 3]
        val.append(val)

        encoder = Serializer(check_circular=False)
        with pytest.raises(RecursionError):
            encoder.encode(val)

    def test_dict_empty(self) -> None:
        val = {}

        encoder = Serializer()
        rep = encoder.encode(val)

        assert rep == MapRep(type="map")
        assert encoder.buffers == []

    def test_dict(self) -> None:
        val = {nan: {1: [2, 3]}, "bcd": None, "abc": True, None: inf}

        encoder = Serializer()
        rep = encoder.encode(val)

        assert rep == MapRep(
            type="map",
            entries=[
                (NumberRep(type="number", value="nan"), MapRep(type="map", entries=[(1, [2, 3])])),
                ("bcd", None),
                ("abc", True),
                (None, NumberRep(type="number", value="+inf")),
            ],
        )
        assert encoder.buffers == []

    def test_dict_circular_with_checking(self) -> None:
        val: dict[Any, Any] = {nan: [1, 2]}
        val[inf] = val

        encoder = Serializer(check_circular=True)
        with pytest.raises(SerializationError, match="circular reference"):
            encoder.encode(val)

    @pytest.mark.skipif(sys.platform == "win32" and sys.version_info < (3, 11), reason="stack overflow instead of RecursionError")
    def test_dict_circular_without_checking(self) -> None:
        val: dict[Any, Any] = {nan: [1, 2]}
        val[inf] = val

        encoder = Serializer(check_circular=False)
        with pytest.raises(RecursionError):
            encoder.encode(val)

    def test_dict_ColumnData(self) -> None:
        val = {"data": PropertyValueColumnData({"col0": [1, 2, 3]})}

        encoder = Serializer()
        rep = encoder.encode(val)

        assert rep == MapRep(
            type="map",
            entries=[(
                "data",
                MapRep(
                    type="map",
                    entries=[("col0", [1, 2, 3])],
                ),
            )],
        )

    def test_SimpleNamespace(self) -> None:
        val = SimpleNamespace(a={1: [2, 3]}, b=None, c=True, d=inf)

        encoder = Serializer()
        rep = encoder.encode(val)

        # TODO StructRep
        assert rep == MapRep(
            type="map",
            entries=[
                ("a", MapRep(type="map", entries=[(1, [2, 3])])),
                ("b", None),
                ("c", True),
                ("d", NumberRep(type="number", value="+inf")),
            ],
        )

    def test_set(self) -> None:
        encoder = Serializer()

        val0: set[int] = set()
        assert encoder.encode(val0) == SetRep(type="set")

        val1 = {1, 2, 3}
        assert encoder.encode(val1) == SetRep(type="set", entries=[1, 2, 3])

    def test_slice(self) -> None:
        encoder = Serializer()

        val0 = slice(2)
        assert encoder.encode(val0) == SliceRep(type="slice", start=None, stop=2, step=None)

        val1 = slice(0, 2)
        assert encoder.encode(val1) == SliceRep(type="slice", start=0, stop=2, step=None)

        val2 = slice(0, 10, 2)
        assert encoder.encode(val2) == SliceRep(type="slice", start=0, stop=10, step=2)

        val3 = slice(0, None, 2)
        assert encoder.encode(val3) == SliceRep(type="slice", start=0, stop=None, step=2)

        val4 = slice(None, None, None)
        assert encoder.encode(val4) == SliceRep(type="slice", start=None, stop=None, step=None)

    def test_bytes(self) -> None:
        encoder = Serializer()
        val = bytes([0xFF, 0x00, 0x17, 0xFE, 0x00])
        rep = encoder.encode(val)

        assert len(encoder.buffers) == 1

        [buf] = encoder.buffers
        assert buf.data == val

        assert rep == BytesRep(type="bytes", data=buf)

    def test_bytes_base64(self) -> None:
        encoder = Serializer(deferred=False)
        val = bytes([0xFF, 0x00, 0x17, 0xFE, 0x00])
        rep = encoder.encode(val)
        assert rep["type"] == "bytes"
        assert gzip.decompress(b64decode(rep["data"])) == val
        assert encoder.buffers == []

    def test_typed_array(self) -> None:
        encoder = Serializer()
        val = TypedArray("i", [0, 1, 2, 3, 4, 5])
        rep = encoder.encode(val)

        assert len(encoder.buffers) == 1

        [buf] = encoder.buffers
        assert bytes(buf.data) == val.tobytes()

        assert rep == TypedArrayRep(
            type="typed_array",
            array=BytesRep(type="bytes", data=buf),
            order=sys.byteorder,
            dtype="int32",
        )

    def test_typed_array_base64(self) -> None:
        encoder = Serializer(deferred=False)
        val = TypedArray("i", [0, 1, 2, 3, 4, 5])
        rep = encoder.encode(val)
        # isinstance not supported for typed dicts, alas
        # assert isinstance(rep, TypedArrayRep)
        assert rep.keys() == {"type", "order", "dtype", "array"}
        assert rep["type"] == "typed_array"
        assert rep["order"] == sys.byteorder
        assert rep["dtype"] == "int32"
        assert rep["array"] == encoder._encode_bytes(memoryview(val))
        assert encoder.buffers == []

    def test_ndarray(self) -> None:
        encoder = Serializer()
        val = np.array([0, 1, 2, 3, 4, 5], dtype="int32")
        rep = encoder.encode(val)

        assert len(encoder.buffers) == 1

        [buf] = encoder.buffers
        assert bytes(buf.data) == val.tobytes()

        assert rep == NDArrayRep(
            type="ndarray",
            array=BytesRep(type="bytes", data=buf),
            order=sys.byteorder,
            shape=[6],
            dtype="int32",
        )

    def test_ndarray_base64(self) -> None:
        encoder = Serializer(deferred=False)
        val = np.array([0, 1, 2, 3, 4, 5], dtype="int32")
        rep = encoder.encode(val)
        # isinstance not supported for typed dicts, alas
        # assert isinstance(rep, NDArrayRep)
        assert rep.keys() == {"type", "order", "shape", "dtype", "array"}
        assert rep["type"] == "ndarray"
        assert rep["order"] == sys.byteorder
        assert rep["shape"] == [6]
        assert rep["dtype"] == "int32"
        assert rep["array"] == encoder._encode_bytes(memoryview(val))
        assert encoder.buffers == []

    def test_ndarray_dtypes_shape(self) -> None:
        encoder = Serializer()

        val0 = np.array([[0, 1, 0], [0, 1, 1]], dtype="bool")
        val1 = np.array([[0, 1, 2], [3, 4, 5]], dtype="uint8")
        val2 = np.array([[0, 1, 2], [3, 4, 5]], dtype="int8")
        val3 = np.array([[0, 1, 2], [3, 4, 5]], dtype="uint16")
        val4 = np.array([[0, 1, 2], [3, 4, 5]], dtype="int16")
        val5 = np.array([[0, 1, 2], [3, 4, 5]], dtype="uint32")
        val6 = np.array([[0, 1, 2], [3, 4, 5]], dtype="int32")
        val7 = np.array([[0, 1, 2], [3, 4, 5]], dtype="uint64")
        val8 = np.array([[0, 1, 2], [3, 4, 5]], dtype="int64")
        val9 = np.array([[0, 1, 2], [3, 4, 5]], dtype="float32")
        val10 = np.array([[0, 1, 2], [3, 4, 5]], dtype="float64")

        rep0 = encoder.encode(val0)
        rep1 = encoder.encode(val1)
        rep2 = encoder.encode(val2)
        rep3 = encoder.encode(val3)
        rep4 = encoder.encode(val4)
        rep5 = encoder.encode(val5)
        rep6 = encoder.encode(val6)
        rep7 = encoder.encode(val7)
        rep8 = encoder.encode(val8)
        rep9 = encoder.encode(val9)
        rep10 = encoder.encode(val10)

        assert len(encoder.buffers) == 11

        assert rep0 == NDArrayRep(
            type="ndarray",
            array=BytesRep(type="bytes", data=encoder.buffers[0]),
            order=sys.byteorder,
            shape=[2, 3],
            dtype="bool",
        )

        assert rep1 == NDArrayRep(
            type="ndarray",
            array=BytesRep(type="bytes", data=encoder.buffers[1]),
            order=sys.byteorder,
            shape=[2, 3],
            dtype="uint8",
        )

        assert rep2 == NDArrayRep(
            type="ndarray",
            array=BytesRep(type="bytes", data=encoder.buffers[2]),
            order=sys.byteorder,
            shape=[2, 3],
            dtype="int8",
        )

        assert rep3 == NDArrayRep(
            type="ndarray",
            array=BytesRep(type="bytes", data=encoder.buffers[3]),
            order=sys.byteorder,
            shape=[2, 3],
            dtype="uint16",
        )

        assert rep4 == NDArrayRep(
            type="ndarray",
            array=BytesRep(type="bytes", data=encoder.buffers[4]),
            order=sys.byteorder,
            shape=[2, 3],
            dtype="int16",
        )

        assert rep5 == NDArrayRep(
            type="ndarray",
            array=BytesRep(type="bytes", data=encoder.buffers[5]),
            order=sys.byteorder,
            shape=[2, 3],
            dtype="uint32",
        )

        assert rep6 == NDArrayRep(
            type="ndarray",
            array=BytesRep(type="bytes", data=encoder.buffers[6]),
            order=sys.byteorder,
            shape=[2, 3],
            dtype="int32",
        )

        assert rep7 == NDArrayRep(
            type="ndarray",
            array=BytesRep(type="bytes", data=Buffer(encoder.buffers[7].id, encoder.buffers[5].data)), # encoder.buffers[7]),
            order=sys.byteorder,
            shape=[2, 3],
            dtype="uint32",
            #dtype="uint64",
        )

        assert rep8 == NDArrayRep(
            type="ndarray",
            array=BytesRep(type="bytes", data=Buffer(encoder.buffers[8].id, encoder.buffers[6].data)), # encoder.buffers[8]),
            order=sys.byteorder,
            shape=[2, 3],
            dtype="int32",
            #dtype="int64",
        )

        assert rep9 == NDArrayRep(
            type="ndarray",
            array=BytesRep(type="bytes", data=encoder.buffers[9]),
            order=sys.byteorder,
            shape=[2, 3],
            dtype="float32",
        )

        assert rep10 == NDArrayRep(
            type="ndarray",
            array=BytesRep(type="bytes", data=encoder.buffers[10]),
            order=sys.byteorder,
            shape=[2, 3],
            dtype="float64",
        )

    def test_ndarray_object(self) -> None:
        @dataclass
        class X:
            f: int = 0
            g: str = "a"

        val = np.array([[X()], [X(1)], [X(2, "b")]])

        encoder = Serializer()
        rep = encoder.encode(val)

        assert rep == NDArrayRep(
            type="ndarray",
            array=[
                ObjectRep(
                    type="object",
                    name="test_serialization.TestSerializer.test_ndarray_object.X",
                    attributes=dict(f=0, g="a"),
                ),
                ObjectRep(
                    type="object",
                    name="test_serialization.TestSerializer.test_ndarray_object.X",
                    attributes=dict(f=1, g="a"),
                ),
                ObjectRep(
                    type="object",
                    name="test_serialization.TestSerializer.test_ndarray_object.X",
                    attributes=dict(f=2, g="b"),
                ),
            ],
            order=sys.byteorder,
            shape=[3, 1],
            dtype="object",
        )
        assert encoder.buffers == []

    def test_ndarray_int64_uint64(self) -> None:
        val0 = np.array([-2**16], dtype="int64")
        val1 = np.array([2**16], dtype="uint64")
        val2 = np.array([-2**36], dtype="int64")
        val3 = np.array([2**36], dtype="uint64")

        encoder = Serializer()

        rep0 = encoder.encode(val0)
        rep1 = encoder.encode(val1)
        rep2 = encoder.encode(val2)
        rep3 = encoder.encode(val3)

        assert len(encoder.buffers) == 2
        [buf0, buf1] = encoder.buffers

        assert rep0 == NDArrayRep(
            type="ndarray",
            array=BytesRep(type="bytes", data=buf0),
            order=sys.byteorder,
            shape=[1],
            dtype="int32",
        )

        assert rep1 == NDArrayRep(
            type="ndarray",
            array=BytesRep(type="bytes", data=buf1),
            order=sys.byteorder,
            shape=[1],
            dtype="uint32",
        )

        assert rep2 == NDArrayRep(
            type="ndarray",
            array=[-2**36],
            order=sys.byteorder,
            shape=[1],
            dtype="object",
        )

        assert rep3 == NDArrayRep(
            type="ndarray",
            array=[2**36],
            order=sys.byteorder,
            shape=[1],
            dtype="object",
        )

    def test_ndarray_zero_dimensional(self):
        encoder = Serializer()

        # floating point
        res = encoder.encode(np.array(2.4))
        assert res == 2.4

        # integer
        res = encoder.encode(np.array(2))
        assert res == 2

    def test_HasProps(self) -> None:
        val = SomeProps(p0=2, p1="a", p2=[1, 2, 3])
        encoder = Serializer()
        rep = encoder.encode(val)
        assert rep == ObjectRep(
            type="object",
            name="test_serialization.SomeProps",
            attributes=dict(
                p0=2,
                p1="a",
                p2=[1, 2, 3],
            ),
        )
        assert encoder.buffers == []

    def test_Model(self) -> None:
        val = SomeModel(p0=3, p1="b", p2=[4, 5, 6])
        encoder = Serializer()
        rep = encoder.encode(val)
        assert rep == ObjectRefRep(
            type="object",
            name="test_serialization.SomeModel",
            id=val.id,
            attributes=dict(
                p0=3,
                p1="b",
                p2=[4, 5, 6],
            ),
        )
        assert encoder.buffers == []

    def test_Model_circular(self) -> None:
        val0 = SomeModel(p0=10)
        val1 = SomeModel(p0=20, p3=val0)
        val2 = SomeModel(p0=30, p3=val1)
        val0.p3 = val2

        encoder = Serializer()
        rep = encoder.encode(val2)

        assert rep == ObjectRefRep(
            type="object",
            name="test_serialization.SomeModel",
            id=val2.id,
            attributes=dict(
                p0=30,
                p3=ObjectRefRep(
                    type="object",
                    name="test_serialization.SomeModel",
                    id=val1.id,
                    attributes=dict(
                        p0=20,
                        p3=ObjectRefRep(
                            type="object",
                            name="test_serialization.SomeModel",
                            id=val0.id,
                            attributes=dict(
                                p0=10,
                                p3=Ref(id=val2.id),
                            ),
                        ),
                    ),
                ),
            ),
        )
        assert encoder.buffers == []

    def test_Model_unset(self) -> None:
        val0 = SomeModelUnset()

        encoder = Serializer()
        with pytest.raises(UnsetValueError):
            encoder.encode(val0)

    def test_dataclass(self) -> None:
        val = SomeDataClass(f0=2, f1=[1, 2, 3])
        encoder = Serializer()
        rep = encoder.encode(val)
        assert rep == ObjectRep(
            type="object",
            name="test_serialization.SomeDataClass",
            attributes=dict(
                f0=2,
                f1=[1, 2, 3],
                f2=None,
            ),
        )
        assert encoder.buffers == []

    def test_dataclass_nested(self) -> None:
        val = SomeDataClass(f0=2, f1=[1, 2, 3], f2=SomeDataClass(f0=3, f1=[4, 5, 6]))
        encoder = Serializer()
        rep = encoder.encode(val)
        assert rep == ObjectRep(
            type="object",
            name="test_serialization.SomeDataClass",
            attributes=dict(
                f0=2,
                f1=[1, 2, 3],
                f2=ObjectRep(
                    type="object",
                    name="test_serialization.SomeDataClass",
                    attributes=dict(
                        f0=3,
                        f1=[4, 5, 6],
                        f2=None,
                    ),
                ),
            ),
        )
        assert encoder.buffers == []

    def test_dataclass_HasProps_nested(self) -> None:
        v0 = SomeProps(p0=2, p1="a", p2=[1, 2, 3])
        val = SomeDataClass(f0=2, f1=[1, 2, 3], f4=v0)
        encoder = Serializer()
        rep = encoder.encode(val)
        assert rep == ObjectRep(
            type="object",
            name="test_serialization.SomeDataClass",
            attributes=dict(
                f0=2,
                f1=[1, 2, 3],
                f2=None,
                f4=ObjectRep(
                    type="object",
                    name="test_serialization.SomeProps",
                    attributes=dict(
                        p0=2,
                        p1="a",
                        p2=[1, 2, 3],
                    ),
                ),
            ),
        )
        assert encoder.buffers == []

    def test_dataclass_Model_nested(self) -> None:
        v0 = SomeModel(p0=3, p1="b", p2=[4, 5, 6])
        val = SomeDataClass(f0=2, f1=[1, 2, 3], f5=v0)
        encoder = Serializer()
        rep = encoder.encode(val)
        assert rep == ObjectRep(
            type="object",
            name="test_serialization.SomeDataClass",
            attributes=dict(
                f0=2,
                f1=[1, 2, 3],
                f2=None,
                f5=ObjectRefRep(
                    type="object",
                    name="test_serialization.SomeModel",
                    id=v0.id,
                    attributes=dict(
                        p0=3,
                        p1="b",
                        p2=[4, 5, 6],
                    ),
                ),
            ),
        )
        assert encoder.buffers == []

    def test_color_rgb(self) -> None:
        val = RGB(16, 32, 64)
        encoder = Serializer()
        rep = encoder.encode(val)
        assert rep == "rgb(16, 32, 64)"
        assert encoder.buffers == []

    def test_color_rgba(self) -> None:
        val = RGB(16, 32, 64, 0.1)
        encoder = Serializer()
        rep = encoder.encode(val)
        assert rep == "rgba(16, 32, 64, 0.1)"
        assert encoder.buffers == []

    def test_pd_series(self) -> None:
        encoder = Serializer()
        val = pd.Series([0, 1, 2, 3, 4, 5], dtype="int32")
        rep = encoder.encode(val)

        assert len(encoder.buffers) == 1
        [buf] = encoder.buffers

        assert rep == NDArrayRep(
            type="ndarray",
            array=BytesRep(type="bytes", data=buf),
            order=sys.byteorder,
            shape=[6],
            dtype="int32",
        )

    def test_np_int64(self) -> None:
        encoder = Serializer()
        val = np.int64(1).item()
        rep = encoder.encode(val)
        assert rep == 1
        assert isinstance(rep, int)

    def test_np_float64(self) -> None:
        encoder = Serializer()
        val = np.float64(1.33)
        rep = encoder.encode(val)
        assert rep == 1.33
        assert isinstance(rep, float)

    def test_np_bool(self) -> None:
        encoder = Serializer()
        val = np.bool_(True)
        rep = encoder.encode(val)
        assert rep is True
        assert isinstance(rep, bool)

    def test_np_datetime64(self) -> None:
        encoder = Serializer()
        val = np.datetime64('2017-01-01')
        rep = encoder.encode(val)
        assert rep == 1483228800000.0
        assert isinstance(rep, float)

    def test_dt_time(self) -> None:
        encoder = Serializer()
        val = dt.time(12, 32, 15)
        rep = encoder.encode(val)
        assert rep == 45135000.0
        assert isinstance(rep, float)

    def test_pd_timestamp(self) -> None:
        encoder = Serializer()
        val = pd.Timestamp('April 28, 1948')
        rep = encoder.encode(val)
        assert rep == -684115200000

    def test_pd_NA(self) -> None:
        encoder = Serializer()
        assert encoder.encode(pd.NA) is None

    def test_other_array_libraries(self) -> None:
        class CustomArray:
            def __init__(self, values, dtype):
                self.values = values
                self.dtype = dtype

            def __array__(self):
                return np.asarray(self.values, dtype=self.dtype)

        encoder = Serializer()
        val1 = CustomArray([[0, 1, 2], [3, 4, 5]], "uint32")
        val2 = np.array([[0, 1, 2], [3, 4, 5]], dtype="uint32")
        rep1 = encoder.encode(val1)
        rep2 = encoder.encode(val2)

        assert len(encoder.buffers) == 2

        assert rep1 == NDArrayRep(
            type="ndarray",
            array=BytesRep(type="bytes", data=encoder.buffers[0]),
            order=sys.byteorder,
            shape=[2, 3],
            dtype="uint32",
        )

        assert rep1["array"]["data"].data == rep2["array"]["data"].data

    def test_self_referential_issue_14383(self) -> None:
        from bokeh.models import CustomJS
        from bokeh.plotting import figure

        p = figure()
        lines = [p.line([1, 2, 3], [1, 2, 3]) for _ in range(3)]

        for line in lines:
            handler = CustomJS(args=dict(lines=lines), code="")
            line.js_on_change("muted", handler)

        encoder = Serializer()
        encoder.encode(p) # no SerializationError("circular reference") error raised here

class TestDeserializer:

    def test_slice(self) -> None:
        decoder = Deserializer()

        rep0 = SliceRep(type="slice", start=None, stop=2, step=None)
        assert decoder.decode(rep0) == slice(2)

        rep1 = SliceRep(type="slice", start=0, stop=2, step=None)
        assert decoder.decode(rep1) == slice(0, 2)

        rep2 = SliceRep(type="slice", start=0, stop=10, step=2)
        assert decoder.decode(rep2) == slice(0, 10, 2)

        rep3 = SliceRep(type="slice", start=0, stop=None, step=2)
        assert decoder.decode(rep3) == slice(0, None, 2)

        rep4 = SliceRep(type="slice", start=None, stop=None, step=None)
        assert decoder.decode(rep4) == slice(None, None, None)

    def test_known_Model(self) -> None:
        val = SomeModel()

        encoder = Serializer()
        rep = encoder.encode(val)

        decoder = Deserializer([val])
        with pytest.warns(BokehUserWarning, match=f"reference already known '{val.id}'"):
            ret = decoder.deserialize(rep)

        assert ret == val

    def test_unknown_type(self) -> None:
        decoder = Deserializer()
        with pytest.raises(DeserializationError):
            decoder.deserialize(dict(type="foo"))

"""
    def test_set_data_from_json_list(self) -> None:
        ds = bms.ColumnDataSource()
        data = {"foo": [1, 2, 3]}
        ds.set_from_json('data', data)
        assert ds.data == data

    def test_set_data_from_json_base64(self) -> None:
        ds = bms.ColumnDataSource()
        data = {"foo": np.arange(3, dtype=np.int64)}
        json = transform_column_source_data(data)
        ds.set_from_json('data', json)
        assert np.array_equal(ds.data["foo"], data["foo"])

    def test_set_data_from_json_nested_base64(self) -> None:
        ds = bms.ColumnDataSource()
        data = {"foo": [[np.arange(3, dtype=np.int64)]]}
        json = transform_column_source_data(data)
        ds.set_from_json('data', json)
        assert np.array_equal(ds.data["foo"], data["foo"])

    def test_set_data_from_json_nested_base64_and_list(self) -> None:
        ds = bms.ColumnDataSource()
        data = {"foo": [np.arange(3, dtype=np.int64), [1, 2, 3]]}
        json = transform_column_source_data(data)
        ds.set_from_json('data', json)
        assert np.array_equal(ds.data["foo"], data["foo"])


class TestSerializeJson:
    def setup_method(self, test_method):
        from json import loads

        from bokeh.core.json_encoder import serialize_json
        self.serialize = serialize_json
        self.deserialize = loads

    def test_with_basic(self) -> None:
        assert self.serialize({'test': [1, 2, 3]}) == '{"test":[1,2,3]}'

    def test_pretty(self) -> None:
        assert self.serialize({'test': [1, 2, 3]}, pretty=True) == '{\n  "test": [\n    1,\n    2,\n    3\n  ]\n}'

    def test_with_np_array(self) -> None:
        a = np.arange(5)
        assert self.serialize(a) == '[0,1,2,3,4]'

    def test_with_pd_series(self) -> None:
        s = pd.Series([0, 1, 2, 3, 4])
        assert self.serialize(s) == '[0,1,2,3,4]'

    def test_nans_and_infs(self) -> None:
        arr = np.array([np.nan, np.inf, -np.inf, 0])
        serialized = self.serialize(arr)
        deserialized = self.deserialize(serialized)
        assert deserialized[0] == 'NaN'
        assert deserialized[1] == 'Infinity'
        assert deserialized[2] == '-Infinity'
        assert deserialized[3] == 0

    def test_nans_and_infs_pandas(self) -> None:
        arr = pd.Series(np.array([np.nan, np.inf, -np.inf, 0]))
        serialized = self.serialize(arr)
        deserialized = self.deserialize(serialized)
        assert deserialized[0] == 'NaN'
        assert deserialized[1] == 'Infinity'
        assert deserialized[2] == '-Infinity'
        assert deserialized[3] == 0

    def test_pandas_datetime_types(self) -> None:
        ''' should convert to millis '''
        idx = pd.date_range('2001-1-1', '2001-1-5')
        df = pd.DataFrame({'vals' :idx}, index=idx)
        serialized = self.serialize({'vals' : df.vals,
                                     'idx' : df.index})
        deserialized = self.deserialize(serialized)
        baseline = {
            "vals": [
                978307200000,
                978393600000,
                978480000000,
                978566400000,
                978652800000,
            ],
            "idx": [
                978307200000,
                978393600000,
                978480000000,
                978566400000,
                978652800000,
            ],
        }
        assert deserialized == baseline

    def test_builtin_datetime_types(self) -> None:
        ''' should convert to millis as-is '''

        DT_EPOCH = dt.datetime.fromtimestamp(0, tz=dt.timezone.utc)

        a = dt.date(2016, 4, 28)
        b = dt.datetime(2016, 4, 28, 2, 20, 50)
        serialized = self.serialize({'a' : [a],
                                     'b' : [b]})
        deserialized = self.deserialize(serialized)

        baseline = {'a': ['2016-04-28'],
                    'b': [(b - DT_EPOCH).total_seconds() * 1000. + b.microsecond / 1000.],
        }
        assert deserialized == baseline

        # test pre-computed values too
        assert deserialized == {
            'a': ['2016-04-28'], 'b': [1461810050000.0]
        }

    def test_builtin_timedelta_types(self) -> None:
        ''' should convert time delta to a dictionary '''
        delta = dt.timedelta(days=42, seconds=1138, microseconds=1337)
        serialized = self.serialize(delta)
        deserialized = self.deserialize(serialized)
        assert deserialized == delta.total_seconds() * 1000

    def test_numpy_timedelta_types(self) -> None:
        delta = np.timedelta64(3000, 'ms')
        serialized = self.serialize(delta)
        deserialized = self.deserialize(serialized)
        assert deserialized == 3000

        delta = np.timedelta64(3000, 's')
        serialized = self.serialize(delta)
        deserialized = self.deserialize(serialized)
        assert deserialized == 3000000

    def test_pandas_timedelta_types(self) -> None:
        delta = pd.Timedelta("3000ms")
        serialized = self.serialize(delta)
        deserialized = self.deserialize(serialized)
        assert deserialized == 3000


@pytest.mark.parametrize('dt', [np.float32, np.float64, np.int64])
@pytest.mark.parametrize('shape', [(12,), (2, 6), (2,2,3)])
def test_encode_base64_dict(dt, shape) -> None:
    a = np.arange(12, dtype=dt)
    a.reshape(shape)
    d = bus.encode_base64_dict(a)

    assert 'shape' in d
    assert d['shape'] == a.shape

    assert 'dtype' in d
    assert d['dtype'] == a.dtype.name

    assert '__ndarray__' in d
    b64 = base64.b64decode(d['__ndarray__'])
    aa = np.frombuffer(b64, dtype=d['dtype'])
    assert np.array_equal(a, aa)

@pytest.mark.parametrize('dt', [np.float32, np.float64, np.int64])
@pytest.mark.parametrize('shape', [(12,), (2, 6), (2,2,3)])
def test_decode_base64_dict(dt, shape) -> None:
    a = np.arange(12, dtype=dt)
    a.reshape(shape)
    data = base64.b64encode(a).decode('utf-8')
    d = {
        '__ndarray__'  : data,
        'dtype'        : a.dtype.name,
        'shape'        : a.shape
    }
    aa = bus.decode_base64_dict(d)

    assert aa.shape == a.shape

    assert aa.dtype.name == a.dtype.name

    assert np.array_equal(a, aa)

    assert aa.flags['WRITEABLE']

@pytest.mark.parametrize('dt', [np.float32, np.float64, np.int64])
@pytest.mark.parametrize('shape', [(12,), (2, 6), (2,2,3)])
def test_encode_decode_roundtrip(dt, shape) -> None:
    a = np.arange(12, dtype=dt)
    a.reshape(shape)
    d = bus.encode_base64_dict(a)
    aa = bus.decode_base64_dict(d)
    assert np.array_equal(a, aa)


@pytest.mark.parametrize('dt', bus.BINARY_ARRAY_TYPES)
@pytest.mark.parametrize('shape', [(12,), (2, 6), (2,2,3)])
def test_encode_binary_dict(dt, shape) -> None:
    a = np.arange(12, dtype=dt)
    a.reshape(shape)
    bufs = []
    d = bus.encode_binary_dict(a, buffers=bufs)

    assert len(bufs) == 1
    assert len(bufs[0]) == 2
    assert bufs[0][1] == a.tobytes()
    assert 'shape' in d
    assert d['shape'] == a.shape

    assert 'dtype' in d
    assert d['dtype'] == a.dtype.name

    assert '__buffer__' in d

@pytest.mark.parametrize('cols', [None, [], ['a'], ['a', 'b'], ['a', 'b', 'c']])
@pytest.mark.parametrize('dt1', [np.float32, np.float64, np.int64])
@pytest.mark.parametrize('dt2', [np.float32, np.float64, np.int64])
def test_transform_column_source_data_with_buffers(pd, cols, dt1, dt2) -> None:
    d = dict(a=[1,2,3], b=np.array([4,5,6], dtype=dt1), c=pd.Series([7,8,9], dtype=dt2))
    bufs = []
    out = bus.transform_column_source_data(d, buffers=bufs, cols=cols)
    assert set(out) == (set(d) if cols is None else set(cols))
    if 'a' in out:
        assert out['a'] == [1,2,3]
    for x in ['b', 'c']:
        dt = d[x].dtype
        if x in out:
            if dt in bus.BINARY_ARRAY_TYPES:
                assert isinstance(out[x], dict)
                assert 'shape' in out[x]
                assert out[x]['shape'] == d[x].shape
                assert 'dtype' in out[x]
                assert out[x]['dtype'] == d[x].dtype.name
                assert '__buffer__' in out[x]
            else:
                assert isinstance(out[x], list)
                assert out[x] == list(d[x])

def test_transform_series_force_list_default_with_buffers() -> None:
    # default int seems to be int64, can't be converted to buffer!
    df = pd.Series([1, 3, 5, 6, 8])
    out = bus.transform_series(df)
    assert isinstance(out, list)
    assert out == [1, 3, 5, 6, 8]

    df = pd.Series([1, 3, 5, 6, 8], dtype=np.int32)
    bufs = []
    out = bus.transform_series(df, buffers=bufs)
    assert isinstance(out, dict)
    assert len(bufs) == 1
    assert len(bufs[0]) == 2
    assert isinstance(bufs[0][0], dict)
    assert list(bufs[0][0]) == ["id"]
    assert bufs[0][1] == np.array(df).tobytes()
    assert 'shape' in out
    assert out['shape'] == df.shape
    assert 'dtype' in out
    assert out['dtype'] == df.dtype.name
    assert '__buffer__' in out

    df = pd.Series([1.0, 3, 5, 6, 8])
    bufs = []
    out = bus.transform_series(df, buffers=bufs)
    assert isinstance(out, dict)
    assert len(bufs) == 1
    assert len(bufs[0]) == 2
    assert isinstance(bufs[0][0], dict)
    assert list(bufs[0][0]) == ["id"]
    assert bufs[0][1] == np.array(df).tobytes()
    assert 'shape' in out
    assert out['shape'] == df.shape
    assert 'dtype' in out
    assert out['dtype'] == df.dtype.name
    assert '__buffer__' in out

    df = pd.Series(np.array([np.nan, np.inf, -np.inf, 0]))
    bufs = []
    out = bus.transform_series(df, buffers=bufs)
    assert isinstance(out, dict)
    assert len(bufs) == 1
    assert len(bufs[0]) == 2
    assert isinstance(bufs[0][0], dict)
    assert list(bufs[0][0]) == ["id"]
    assert bufs[0][1] == np.array(df).tobytes()
    assert 'shape' in out
    assert out['shape'] == df.shape
    assert 'dtype' in out
    assert out['dtype'] == df.dtype.name
    assert '__buffer__' in out

    # PeriodIndex
    df = pd.period_range('1900-01-01','2000-01-01', freq='A')
    bufs = []
    out = bus.transform_series(df, buffers=bufs)
    assert isinstance(out, dict)
    assert len(bufs) == 1
    assert len(bufs[0]) == 2
    assert isinstance(bufs[0][0], dict)
    assert list(bufs[0][0]) == ["id"]
    assert bufs[0][1] == bus.convert_datetime_array(df.to_timestamp().values).tobytes()
    assert 'shape' in out
    assert out['shape'] == df.shape
    assert 'dtype' in out
    assert out['dtype'] == 'float64'
    assert '__buffer__' in out

    # DatetimeIndex
    df = pd.period_range('1900-01-01','2000-01-01', freq='A').to_timestamp()
    bufs = []
    out = bus.transform_series(df, buffers=bufs)
    assert isinstance(out, dict)
    assert len(bufs) == 1
    assert len(bufs[0]) == 2
    assert isinstance(bufs[0][0], dict)
    assert list(bufs[0][0]) == ["id"]
    assert bufs[0][1] == bus.convert_datetime_array(df.values).tobytes()
    assert 'shape' in out
    assert out['shape'] == df.shape
    assert 'dtype' in out
    assert out['dtype'] == 'float64'
    assert '__buffer__' in out

    # TimeDeltaIndex
    df = pd.to_timedelta(np.arange(5), unit='s')
    bufs = []
    out = bus.transform_series(df, buffers=bufs)
    assert isinstance(out, dict)
    assert len(bufs) == 1
    assert len(bufs[0]) == 2
    assert isinstance(bufs[0][0], dict)
    assert list(bufs[0][0]) == ["id"]
    assert bufs[0][1] == bus.convert_datetime_array(df.values).tobytes()
    assert 'shape' in out
    assert out['shape'] == df.shape
    assert 'dtype' in out
    assert out['dtype'] == 'float64'
    assert '__buffer__' in out

    def test_to_json(self) -> None:
        child_obj = SomeModelToJson(foo=57, bar="hello")
        obj = SomeModelToJson(child=child_obj, foo=42, bar="world")

        json = obj.to_json(include_defaults=True)
        json_string = serialize_json(json)

        assert json == {
            "child": {"id": child_obj.id},
            "null_child": None,
            "id": obj.id,
            "name": None,
            "tags": [],
            'js_property_callbacks': dict(type="map", entries=[]),
            "js_event_callbacks": dict(type="map", entries=[]),
            "subscribed_events": dict(type="set", entries=[]),
            "syncable": True,
            "foo": 42,
            "bar": "world",
        }
        assert (
            '{"bar":"world",' +
            '"child":{"id":"%s"},' +
            '"foo":42,' +
            '"id":"%s",' +
            '"js_event_callbacks":{"entries":[],"type":"map"},' +
            '"js_property_callbacks":{"entries":[],"type":"map"},' +
            '"name":null,' +
            '"null_child":null,' +
            '"subscribed_events":{"entries":[],"type":"set"},' +
            '"syncable":true,' +
            '"tags":[]}'
        ) % (child_obj.id, obj.id) == json_string

        json = obj.to_json(include_defaults=False)
        json_string = serialize_json(json)

        assert json == {
            "child": {"id": child_obj.id},
            "id": obj.id,
            "foo": 42,
            "bar": "world",
        }
        assert (
            '{"bar":"world",' +
            '"child":{"id":"%s"},' +
            '"foo":42,' +
            '"id":"%s"}'
        ) % (child_obj.id, obj.id) == json_string

    def test_no_units_in_json(self) -> None:
        from bokeh.models import AnnularWedge
        obj = AnnularWedge()
        json = obj.to_json(include_defaults=True)
        assert 'start_angle' in json
        assert 'start_angle_units' not in json
        assert 'outer_radius' in json
        assert 'outer_radius_units' not in json

    def test_dataspec_field_in_json(self) -> None:
        from bokeh.models import AnnularWedge
        obj = AnnularWedge()
        obj.start_angle = "fieldname"
        json = obj.to_json(include_defaults=True)
        assert 'start_angle' in json
        assert 'start_angle_units' not in json
        assert json["start_angle"] == dict(type="map", entries=[["field", "fieldname"]]) # TODO: dict(type="field", field="fieldname")

    def test_dataspec_value_in_json(self) -> None:
        from bokeh.models import AnnularWedge
        obj = AnnularWedge()
        obj.start_angle = 60
        json = obj.to_json(include_defaults=True)
        assert 'start_angle' in json
        assert 'start_angle_units' not in json
        assert json["start_angle"] == dict(type="map", entries=[["value", 60]]) # TODO: dict(type="value", value=60)


"""

#-----------------------------------------------------------------------------
# Private API
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Code
#-----------------------------------------------------------------------------
