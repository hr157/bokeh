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
import logging

# Bokeh imports
from tests.support.util.api import verify_all
from tests.support.util.env import envset

# Module under test
import bokeh.settings as bs # isort:skip

#-----------------------------------------------------------------------------
# Setup
#-----------------------------------------------------------------------------

ALL = (
    'settings',
)

logging.basicConfig(level=logging.DEBUG)

#-----------------------------------------------------------------------------
# General API
#-----------------------------------------------------------------------------

Test___all__ = verify_all(bs, ALL)

_expected_settings = (
    'allowed_ws_origin',
    'auth_module',
    'browser',
    'cdn_version',
    'chromedriver_path',
    'compression_level',
    'cookie_secret',
    'default_server_host',
    'default_server_port',
    'docs_cdn',
    'docs_version',
    'ico_path',
    'ignore_filename',
    'log_level',
    'minified',
    'nodejs_path',
    'perform_document_validation',
    'pretty',
    'py_log_level',
    'resources',
    'rootdir',
    'secret_key',
    'serialize_include_defaults',
    'sign_sessions',
    'simple_ids',
    'ssl_certfile',
    'ssl_keyfile',
    'ssl_password',
    'validation_level',
    'xsrf_cookies',
)


class TestSettings:
    def test_standard_settings(self) -> None:
        settings = [k for k,v in bs.settings.__class__.__dict__.items() if isinstance(v, bs.PrioritizedSetting)]
        assert set(settings) == set(_expected_settings)

    @pytest.mark.parametrize("name", _expected_settings)
    def test_prefix(self, name: str) -> None:
        ps = getattr(bs.settings, name)
        assert ps.env_var.startswith("BOKEH_")

    @pytest.mark.parametrize("name", _expected_settings)
    def test_parent(self, name: str) -> None:
        ps = getattr(bs.settings, name)
        assert ps._parent == bs.settings

    def test_types(self) -> None:
        assert bs.settings.ignore_filename.convert_type == "Bool"
        assert bs.settings.minified.convert_type == "Bool"
        assert bs.settings.perform_document_validation.convert_type == "Bool"
        assert bs.settings.simple_ids.convert_type == "Bool"
        assert bs.settings.xsrf_cookies.convert_type == "Bool"

        assert bs.settings.default_server_port.convert_type == "Int"

        assert bs.settings.compression_level.convert_type == "Compression Level (0-9)"

        assert bs.settings.py_log_level.convert_type == "Log Level"

        assert bs.settings.validation_level.convert_type == "Validation Level"

        assert bs.settings.allowed_ws_origin.convert_type == "List[String]"

        assert bs.settings.ico_path.convert_type == "Ico Path"

        default_typed = set(_expected_settings) - {
            'allowed_ws_origin',
            'compression_level',
            'default_server_port',
            'ico_path',
            'ignore_filename',
            'minified',
            'perform_document_validation',
            'py_log_level',
            'simple_ids',
            'validation_level',
            'xsrf_cookies',
        }
        for name in default_typed:
            ps = getattr(bs.settings, name)
            assert ps.convert_type == "String"

#-----------------------------------------------------------------------------
# Dev API
#-----------------------------------------------------------------------------

class TestConverters:
    @pytest.mark.parametrize("value", ["Yes", "YES", "yes", "1", "ON", "on", "true", "True", True])
    def test_convert_bool(self, value: str | bool) -> None:
        assert bs.convert_bool(value)

    @pytest.mark.parametrize("value", ["No", "NO", "no", "0", "OFF", "off", "false", "False", False])
    def test_convert_bool_false(self, value: str | bool) -> None:
        assert not bs.convert_bool(value)

    @pytest.mark.parametrize("value", [True, False])
    def test_convert_bool_identity(self, value: bool) -> None:
        assert bs.convert_bool(value) == value

    def test_convert_bool_bad(self) -> None:
        with pytest.raises(ValueError):
            bs.convert_bool("junk")

    @pytest.mark.parametrize("value", ["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"])
    def test_convert_logging_good(self, value: str) -> None:
        assert bs.convert_logging(value) == getattr(logging, value)

        # check lowercase works too
        assert bs.convert_logging(value.lower()) == getattr(logging, value)

    def test_convert_logging_none(self) -> None:
        assert bs.convert_logging("NONE") is None

        # check lowercase works
        assert bs.convert_logging("none") is None

        # check value works
        assert bs.convert_logging(None) is None

    @pytest.mark.parametrize("value", ["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"])
    def test_convert_logging_identity(self, value: str) -> None:
        level = getattr(logging, value)
        assert bs.convert_logging(level) == level

    def test_convert_logging_bad(self) -> None:
        with pytest.raises(ValueError):
            bs.convert_logging("junk")

    @pytest.mark.parametrize("value", ["none", "errors", "all"])
    def test_convert_validation_good(self, value: str) -> None:
        assert bs.convert_validation(value) == value

    def test_convert_validation_bad(self) -> None:
        with pytest.raises(ValueError):
            bs.convert_validation("junk")

    @pytest.mark.parametrize("value", ["none", "NONE", "None"])
    def test_convert_ico_path_none(self, value: str) -> None:
        assert bs.convert_ico_path(value) == "none"

    def test_convert_ico_path_default(self) -> None:
        assert bs.convert_ico_path("default").endswith("bokeh.ico")
        assert bs.convert_ico_path("default-dev").endswith("bokeh-dev.ico")

    def test_convert_ico_path_good(self) -> None:
        assert bs.convert_ico_path("/foo/bar.ico") == "/foo/bar.ico"

    def test_convert_ico_path_bad(self) -> None:
        with pytest.raises(ValueError):
            bs.convert_ico_path("junk")

class TestPrioritizedSetting:
    def test_env_var_property(self) -> None:
        ps = bs.PrioritizedSetting("foo", env_var="BOKEH_FOO")
        assert ps.env_var == "BOKEH_FOO"

    def test_everything_unset_raises(self) -> None:
        ps = bs.PrioritizedSetting("foo")
        with pytest.raises(RuntimeError):
            ps()

    def test_implict_default(self) -> None:
        ps = bs.PrioritizedSetting("foo", default=10)
        assert ps() == 10

    def test_implict_default_converts(self) -> None:
        ps = bs.PrioritizedSetting("foo", convert=int, default="10")
        assert ps() == 10

    def test_help(self) -> None:
        ps = bs.PrioritizedSetting("foo", env_var="BOKEH_FOO", default=10, help="bar")
        assert ps.help == "bar"

    def test_name(self) -> None:
        ps = bs.PrioritizedSetting("foo", env_var="BOKEH_FOO", default=10)
        assert ps.name == "foo"

    def test_global_default(self) -> None:
        ps = bs.PrioritizedSetting("foo", env_var="BOKEH_FOO", default=10)
        assert ps.default == 10
        assert ps() == 10

    def test_local_default(self) -> None:
        ps = bs.PrioritizedSetting("foo", env_var="BOKEH_FOO", default=10)
        assert ps.default == 10
        assert ps(default=20) == 20

    def test_dev_default(self) -> None:
        ps = bs.PrioritizedSetting("foo", env_var="BOKEH_FOO", default=10, dev_default=25)
        assert ps.dev_default == 25
        with envset(BOKEH_DEV="yes"):
            assert ps() == 25
            assert ps(default=20) == 25

    def test_env_var(self) -> None:
        with envset(BOKEH_FOO="30"):
            ps = bs.PrioritizedSetting("foo", env_var="BOKEH_FOO")
            assert ps.env_var == "BOKEH_FOO"
            assert ps() == "30"
            assert ps(default=20) == "30"

    def test_env_var_converts(self) -> None:
        with envset(BOKEH_FOO="30"):
            ps = bs.PrioritizedSetting("foo", convert=int, env_var="BOKEH_FOO")
            assert ps() == 30

    def test_user_set(self) -> None:
        ps = bs.PrioritizedSetting("foo")
        ps.set_value(40)
        assert ps() == 40
        assert ps(default=20) == 40

    def test_user_unset(self) -> None:
        ps = bs.PrioritizedSetting("foo", default=2)
        ps.set_value(40)
        assert ps() == 40
        ps.unset_value()
        assert ps() == 2

    def test_user_set_converts(self) -> None:
        ps = bs.PrioritizedSetting("foo", convert=int)
        ps.set_value("40")
        assert ps() == 40

    def test_immediate(self) -> None:
        ps = bs.PrioritizedSetting("foo")
        assert ps(50) == 50
        assert ps(50, default=20) == 50

    def test_immediate_converts(self) -> None:
        ps = bs.PrioritizedSetting("foo", convert=int)
        assert ps("50") == 50

    def test_precedence(self) -> None:
        class FakeSettings:
            config_override = {}
            config_user = {}
            config_system = {}

        ps = bs.PrioritizedSetting("foo", env_var="BOKEH_FOO", convert=int, default=0, dev_default=15)
        ps._parent = FakeSettings

        # 0. global default
        assert ps() == 0

        # 1. local default
        assert ps(default=10) == 10

        # 1.5. implicit default (DEV)
        with envset(BOKEH_DEV="yes"):
            assert ps() == 15

        # 2. global config file
        FakeSettings.config_system['foo'] = 20
        assert ps() == 20
        assert ps(default=10) == 20

        # 3. local config file
        FakeSettings.config_user['foo'] = 30
        assert ps() == 30
        assert ps(default=10) == 30

        # 4. environment variable
        with envset(BOKEH_FOO="40"):
            assert ps() == 40
            assert ps(default=10) == 40

            # 5. override config file
            FakeSettings.config_override['foo'] = 50
            assert ps() == 50
            assert ps(default=10) == 50

            # 6. previously user-set value
            ps.set_value(60)
            assert ps() == 60
            assert ps(default=10) == 60

            # 7. immediate values
            assert ps(70) == 70
            assert ps(70, default=10) == 70

    def test_descriptors(self) -> None:
        class FakeSettings:
            foo = bs.PrioritizedSetting("foo", env_var="BOKEH_FOO")
            bar = bs.PrioritizedSetting("bar", env_var="BOKEH_BAR", default=10)

        s = FakeSettings()
        assert s.foo is FakeSettings.foo

        assert s.bar() == 10
        s.bar = 20
        assert s.bar() == 20
        del s.bar
        assert s.bar() == 10

class TestDefaults:

    def test_allowed_ws_origin(self):
        assert bs.settings.allowed_ws_origin.default == []

    def test_auth_module(self):
        assert bs.settings.auth_module.default is None

    def test_browser(self):
        assert bs.settings.browser.default is None

    def test_cdn_version(self):
        assert bs.settings.cdn_version.default is None

    def test_chromedriver_path(self):
        assert bs.settings.chromedriver_path.default is None

    def test_cookie_secret(self):
        assert bs.settings.cookie_secret.default is None

    def test_docs_cdn(self):
        assert bs.settings.docs_cdn.default is None

    def test_docs_version(self):
        assert bs.settings.docs_version.default is None

    def test_ico_path(self):
        assert bs.settings.ico_path.default == "default"

    def test_ignore_filename(self):
        assert bs.settings.ignore_filename.default is False

    def test_log_level(self):
        assert bs.settings.log_level.default == "info"

    def test_minified(self):
        assert bs.settings.minified.default is True

    def test_nodejs_path(self):
        assert bs.settings.nodejs_path.default is None

    def test_perform_document_validation(self):
        assert bs.settings.perform_document_validation.default is True

    def test_pretty(self):
        assert bs.settings.pretty.default is False

    def test_py_log_level(self):
        assert bs.settings.py_log_level.default == "none"

    def test_resources(self):
        assert bs.settings.resources.default == "cdn"

    def test_rootdir(self):
        assert bs.settings.rootdir.default is None

    def test_secret_key(self):
        assert bs.settings.secret_key.default is None

    def test_serialize_include_defaults(self):
        assert bs.settings.serialize_include_defaults.default is False

    def test_sign_sessions(self):
        assert bs.settings.sign_sessions.default is False

    def test_simple_ids(self):
        assert bs.settings.simple_ids.default is True

    def test_ssl_certfile(self):
        assert bs.settings.ssl_certfile.default is None

    def test_ssl_keyfile(self):
        assert bs.settings.ssl_keyfile.default is None

    def test_ssl_password(self):
        assert bs.settings.ssl_password.default is None

    def test_validation_level(self):
        assert bs.settings.validation_level.default == "none"

    def test_xsrf_cookies(self):
        assert bs.settings.xsrf_cookies.default is False


#-----------------------------------------------------------------------------
# Private API
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Code
#-----------------------------------------------------------------------------
