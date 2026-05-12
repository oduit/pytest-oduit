import os
import socket
import subprocess
import sys
import tempfile
import textwrap
import types
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock, patch

import pytest
from _pytest import pathlib as pytest_pathlib

from pytest_oduit import (
    _configure_random_http_port,
    _extract_addon_name,
    _find_manifest_path,
    _find_unknown_odoo_options,
    _get_available_random_port,
    _require_odoo_runtime_modules,
    _validate_generated_odoo_options,
    disable_odoo_test_retry,
    get_odoo_version,
    monkey_patch_resolve_pkg_root_and_module_name,
    pytest_cmdline_main,
    pytest_runtest_call,
    pytest_runtest_setup,
    support_subtest,
)


class TestPytestOduit(TestCase):
    @contextmanager
    def fake_module(self, with_manifest=True, using_addons_namespace=False):
        directory = tempfile.TemporaryDirectory()
        try:
            module_path = Path(directory.name)
            files = []
            if using_addons_namespace:
                files.append(module_path / "odoo" / "__init__.py")
                files.append(module_path / "odoo" / "addons" / "__init__.py")
                module_path = module_path / "odoo" / "addons" / "my_module"
                module_path.mkdir(parents=True, exist_ok=True)
            manifest_path = None
            if with_manifest:
                manifest_path = module_path / "__manifest__.py"
                files.append(manifest_path)
            test_path = module_path / "tests" / "test_module.py"
            test_path.parent.mkdir(parents=True, exist_ok=True)
            files.append(test_path)
            files.append(module_path / "__init__.py")
            files.append(module_path / "tests" / "__init__.py")
            for file_path in files:
                file_path.touch()
            yield (
                module_path,
                manifest_path,
                test_path,
            )
        finally:
            directory.cleanup()

    def test_find_manifest_path_less_than_5_directories(self):
        self.assertIsNone(_find_manifest_path(Path("/some/path")))

    def test_find_manifest_path_from_test_module(self):
        with self.fake_module() as (_, manifest_path, test_path):
            self.assertEqual(_find_manifest_path(test_path), manifest_path)

    def test_find_manifest_path_from_itself(self):
        with self.fake_module() as (_, manifest_path, _):
            self.assertEqual(_find_manifest_path(manifest_path), manifest_path)

    def test_find_manifest_path_from_brother(self):
        with self.fake_module() as (module_path, manifest_path, _):
            test = module_path / "test_something.py"
            test.touch()
            self.assertEqual(_find_manifest_path(test), manifest_path)

    def test_resolve_pkg_root_and_module_name(self):
        monkey_patch_resolve_pkg_root_and_module_name()
        with self.fake_module() as (module_path, _, test_path):
            pkg_root, module_name = pytest_pathlib.resolve_pkg_root_and_module_name(
                test_path
            )
            self.assertEqual(
                module_name, f"odoo.addons.{module_path.name}.tests.test_module"
            )

    def test_resolve_pkg_root_and_module_name_not_odoo_module(self):
        monkey_patch_resolve_pkg_root_and_module_name()

        with self.fake_module(with_manifest=False) as (module_path, _, test_path):
            pkg_root, module_name = pytest_pathlib.resolve_pkg_root_and_module_name(
                test_path
            )
            self.assertEqual(module_name, f"{module_path.name}.tests.test_module")

    def test_resolve_pkg_root_and_module_name_namespace_ok(self):
        monkey_patch_resolve_pkg_root_and_module_name()

        with self.fake_module(with_manifest=True, using_addons_namespace=True) as (
            module_path,
            _,
            test_path,
        ):
            pkg_root, module_name = pytest_pathlib.resolve_pkg_root_and_module_name(
                test_path
            )
            self.assertEqual(module_name, "odoo.addons.my_module.tests.test_module")

    def test_disable_odoo_test_retry(self):
        from odoo.tests import BaseCase

        original_basecase_run = BaseCase.run

        def restore_basecase_run():
            BaseCase.run = original_basecase_run

        self.addCleanup(restore_basecase_run)

        disable_odoo_test_retry()
        self.assertNotIn("run", BaseCase.__dict__)
        from odoo.tests.case import TestCase

        self.assertIs(BaseCase.run, TestCase.run)

    def test_disable_odoo_test_retry_ignore_run_doesnt_exists(self):
        from odoo.tests import BaseCase

        original_basecase_run = BaseCase.run

        def restore_basecase_run():
            BaseCase.run = original_basecase_run

        self.addCleanup(restore_basecase_run)

        del BaseCase.run

        disable_odoo_test_retry()
        self.assertNotIn("run", BaseCase.__dict__)
        from odoo.tests.case import TestCase

        self.assertIs(BaseCase.run, TestCase.run)

    def test_import_error(self):
        from odoo import tests

        original_BaseCase = tests.BaseCase

        def restore_basecase():
            tests.BaseCase = original_BaseCase

        self.addCleanup(restore_basecase)
        del tests.BaseCase
        disable_odoo_test_retry()

    def test_support_subtest(self):
        from odoo.tests import case

        original_test_case = case.TestCase

        def restore():
            case.TestCase = original_test_case

        self.addCleanup(restore)
        support_subtest()

        from odoo.tests import BaseCase
        from odoo.tests.case import TestCase as OdooTestCase

        if get_odoo_version() < (18,):
            self.assertTrue(OdooTestCase.subTest is TestCase.subTest)
            self.assertTrue(BaseCase.subTest is TestCase.subTest)
            self.assertTrue(OdooTestCase.run is TestCase.run)
        else:
            self.assertFalse(OdooTestCase.subTest is TestCase.subTest)
            self.assertFalse(BaseCase.subTest is TestCase.subTest)
            self.assertFalse(OdooTestCase.run is TestCase.run)

    def test_support_subtest_import_error(self):
        from odoo.tests import case

        original_odoo_test_case = case.TestCase

        def restore_testcase():
            case.TestCase = original_odoo_test_case

        self.addCleanup(restore_testcase)

        del case.TestCase
        support_subtest()

    def test_support_subtest_does_not_patch_run_for_odoo_18_plus(self):
        from odoo.tests.case import TestCase as OdooTestCase

        original_run = OdooTestCase.run
        original_subtest = OdooTestCase.subTest

        def restore_testcase_methods():
            OdooTestCase.run = original_run
            OdooTestCase.subTest = original_subtest

        self.addCleanup(restore_testcase_methods)

        with patch(
            "pytest_oduit.get_odoo_version",
            return_value=(18, 0, 0, "final", 0, ""),
        ):
            support_subtest()

        self.assertFalse(OdooTestCase.subTest is TestCase.subTest)
        self.assertTrue(OdooTestCase.run is original_run)

    def test_support_subtest_adds_missing_outcome_flag_for_odoo_18_plus(self):
        from odoo.tests.case import TestCase as OdooTestCase

        original_subtest = OdooTestCase.subTest

        def restore_testcase_methods():
            OdooTestCase.subTest = original_subtest

        self.addCleanup(restore_testcase_methods)

        with patch(
            "pytest_oduit.get_odoo_version",
            return_value=(18, 0, 0, "final", 0, ""),
        ):
            support_subtest()

        case = OdooTestCase()
        case._outcome = SimpleNamespace(result=None)
        with case.subTest("compat"):
            pass

        self.assertFalse(case._outcome.result_supports_subtests)

    def test_support_subtest_falls_back_when_subtest_kwarg_is_unsupported(self):
        from odoo.tests.case import TestCase as OdooTestCase

        original_subtest = OdooTestCase.subTest

        def restore_testcase_methods():
            OdooTestCase.subTest = original_subtest

        self.addCleanup(restore_testcase_methods)

        with patch(
            "pytest_oduit.get_odoo_version",
            return_value=(18, 0, 0, "final", 0, ""),
        ):
            support_subtest()

        calls = []

        class Outcome:
            def __init__(self):
                self.result = SimpleNamespace(
                    addSubTest=lambda *args, **kwargs: None,
                    failfast=False,
                )
                self.success = True
                self.expectedFailure = False

            def testPartExecutor(self, _case, **kwargs):
                if "subTest" in kwargs:
                    raise TypeError(
                        "testPartExecutor() got an unexpected keyword argument "
                        "'subTest'"
                    )
                calls.append(kwargs)

                @contextmanager
                def _executor():
                    yield

                return _executor()

        case = OdooTestCase()
        case._outcome = Outcome()
        case._subtest = None
        case.failureException = AssertionError
        with case.subTest("compat"):
            pass

        self.assertEqual(calls, [{"isTest": True}])

    def test_support_subtest_patches_run_for_odoo_17(self):
        from odoo.tests.case import TestCase as OdooTestCase

        original_run = OdooTestCase.run
        original_subtest = OdooTestCase.subTest

        def restore_testcase_methods():
            OdooTestCase.run = original_run
            OdooTestCase.subTest = original_subtest

        self.addCleanup(restore_testcase_methods)

        with patch(
            "pytest_oduit.get_odoo_version",
            return_value=(17, 0, 0, "final", 0, ""),
        ):
            support_subtest()

        self.assertTrue(OdooTestCase.subTest is TestCase.subTest)
        self.assertTrue(OdooTestCase.run is TestCase.run)


class TestHttpHelpers(TestCase):
    def test_get_available_random_port_returns_bindable_port(self):
        port = _get_available_random_port()
        self.assertIsInstance(port, int)
        self.assertGreater(port, 0)

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", port))

    def test_configure_random_http_port_sets_odoo_config(self):
        fake_config = {}

        with patch("pytest_oduit.odoo.tools.config", fake_config):
            port = _configure_random_http_port()

        self.assertEqual(fake_config["http_port"], port)

    def test_require_odoo_runtime_modules_accepts_namespace_package(self):
        module_names = (
            "odoo.modules.module",
            "odoo.modules.registry",
            "odoo.service.db",
            "odoo.service.server",
            "odoo.sql_db",
            "odoo.tests.common",
            "odoo.tools",
        )
        modules = {name: types.ModuleType(name) for name in module_names}

        with patch.dict(sys.modules, modules):
            _require_odoo_runtime_modules("/tmp/.oduit.toml")

    def test_require_odoo_runtime_modules_reports_missing_dependency(self):
        with (
            patch("pytest_oduit.importlib.import_module", side_effect=ImportError),
            pytest.raises(pytest.UsageError) as exc_info,
        ):
            _require_odoo_runtime_modules("/tmp/.oduit.toml")

        self.assertIn("could not import 'odoo.modules.module'", str(exc_info.value))

    def _run_cmdline_main(self, *, odoo_http):
        @contextmanager
        def _manage_environment():
            yield

        class FakeOdooConfig(dict):
            parser = SimpleNamespace(_long_opt={}, _short_opt={})

            def parse_config(self, options):
                self["parsed_options"] = options

        fake_odoo_config = FakeOdooConfig(db_name="")
        fake_server = SimpleNamespace(httpd=None, http_spawn=MagicMock())
        fake_odoo = SimpleNamespace(
            tools=SimpleNamespace(config=fake_odoo_config),
            service=SimpleNamespace(
                server=SimpleNamespace(start=MagicMock(), server=fake_server),
                db=SimpleNamespace(_create_empty_database=MagicMock()),
            ),
            api=SimpleNamespace(
                Environment=SimpleNamespace(manage=_manage_environment)
            ),
        )

        options = {
            "--oduit-env": "/tmp/.oduit.toml",
            "--odoo-log-level": "critical",
            "--odoo-http": odoo_http,
            "--odoo-install": "",
        }

        class FakePytestConfig:
            args = []

            def __init__(self, values):
                self._values = values

            def getoption(self, name):
                return self._values.get(name)

        config = FakePytestConfig(options)

        with (
            patch("pytest_oduit._require_odoo_for_active_run"),
            patch("pytest_oduit._require_odoo_runtime_modules"),
            patch("pytest_oduit._build_odoo_config_with_oduit_core", return_value=[]),
            patch("pytest_oduit._validate_generated_odoo_options"),
            patch("pytest_oduit.support_subtest"),
            patch("pytest_oduit.disable_odoo_test_retry"),
            patch("pytest_oduit.monkey_patch_resolve_pkg_root_and_module_name"),
            patch("pytest_oduit.signal.signal"),
            patch(
                "pytest_oduit.get_odoo_version",
                return_value=(18, 0, 0, "final", 0, ""),
            ),
            patch("pytest_oduit.odoo", fake_odoo),
        ):
            hook = pytest_cmdline_main(config)
            next(hook)
            with self.assertRaises(StopIteration):
                next(hook)

        return fake_odoo

    def test_pytest_cmdline_main_does_not_spawn_http_without_option(self):
        fake_odoo = self._run_cmdline_main(odoo_http=False)
        fake_odoo.service.server.server.http_spawn.assert_not_called()
        self.assertNotIn("http_port", fake_odoo.tools.config)

    def test_pytest_cmdline_main_spawns_http_with_random_port_when_enabled(self):
        fake_odoo = self._run_cmdline_main(odoo_http=True)
        fake_odoo.service.server.server.http_spawn.assert_called_once_with()
        self.assertIsInstance(fake_odoo.tools.config["http_port"], int)
        self.assertGreater(fake_odoo.tools.config["http_port"], 0)


class TestHttpCaseSkipping(TestCase):
    @staticmethod
    def _make_item(*, active, odoo_http, instance):
        class FakeConfig:
            def __init__(self):
                self._oduit_active = active

            def getoption(self, name):
                if name == "--odoo-http":
                    return odoo_http
                return None

        return SimpleNamespace(
            config=FakeConfig(),
            instance=instance,
            nodeid="tests/test_http.py::TestHttp::test_case",
        )

    def test_pytest_runtest_setup_is_inert_for_inactive_run(self):
        from odoo.tests.common import HttpCase

        item = self._make_item(active=False, odoo_http=False, instance=HttpCase())
        self.assertIsNone(pytest_runtest_setup(item))

    def test_pytest_runtest_setup_does_not_skip_non_httpcase(self):
        item = self._make_item(active=True, odoo_http=False, instance=object())
        self.assertIsNone(pytest_runtest_setup(item))

    def test_pytest_runtest_setup_skips_httpcase_without_http(self):
        from odoo.tests.common import HttpCase

        item = self._make_item(active=True, odoo_http=False, instance=HttpCase())
        with pytest.raises(pytest.skip.Exception) as exc_info:
            pytest_runtest_setup(item)

        self.assertIn("--odoo-http", str(exc_info.value))

    def test_pytest_runtest_setup_does_not_skip_httpcase_with_http(self):
        from odoo.tests.common import HttpCase

        item = self._make_item(active=True, odoo_http=True, instance=HttpCase())
        self.assertIsNone(pytest_runtest_setup(item))

    def test_pytest_runtest_setup_ignores_missing_httpcase_symbol(self):
        item = self._make_item(active=True, odoo_http=False, instance=object())
        fake_common = types.ModuleType("odoo.tests.common")

        with patch.dict(sys.modules, {"odoo.tests.common": fake_common}):
            self.assertIsNone(pytest_runtest_setup(item))


class TestCurrentTestLifecycle(TestCase):
    def test_pytest_runtest_call_sets_and_resets_current_test_for_odoo_18(self):
        from odoo.tests import BaseCase

        config = SimpleNamespace(_oduit_active=True, getoption=lambda name: None)
        case = BaseCase()
        item = SimpleNamespace(config=config, instance=case)

        with patch(
            "pytest_oduit.get_odoo_version",
            return_value=(18, 0, 0, "final", 0, ""),
        ):
            hook = pytest_runtest_call(item)
            next(hook)
            self.assertIs(sys.modules["odoo"].modules.module.current_test, case)
            with self.assertRaises(StopIteration):
                next(hook)

        self.assertFalse(sys.modules["odoo"].modules.module.current_test)


class TestExtractAddonName(TestCase):
    @contextmanager
    def create_addon_structure(self, addon_name="test_addon"):
        """Create a temporary addon structure with __manifest__.py file."""
        directory = tempfile.TemporaryDirectory()
        try:
            addon_path = Path(directory.name) / "addons" / addon_name
            addon_path.mkdir(parents=True, exist_ok=True)

            # Create __manifest__.py
            manifest_path = addon_path / "__manifest__.py"
            manifest_path.write_text("{'name': 'Test Addon', 'installable': True}")

            # Create tests directory
            tests_path = addon_path / "tests"
            tests_path.mkdir(exist_ok=True)

            # Create test file
            test_file = tests_path / "test_something.py"
            test_file.touch()

            yield {
                "addon_path": addon_path,
                "test_file": test_file,
                "tests_dir": tests_path,
                "manifest": manifest_path,
            }
        finally:
            directory.cleanup()

    def test_extract_addon_name_from_addon_directory(self):
        """Test extracting addon name when path is the addon directory itself."""
        with self.create_addon_structure("sale") as paths:
            addon_name = _extract_addon_name(paths["addon_path"])
            self.assertEqual(addon_name, "sale")

    def test_extract_addon_name_from_test_file(self):
        """Test extracting addon name from a test file path."""
        with self.create_addon_structure("purchase") as paths:
            addon_name = _extract_addon_name(paths["test_file"])
            self.assertEqual(addon_name, "purchase")

    def test_extract_addon_name_from_tests_directory(self):
        """Test extracting addon name from tests directory."""
        with self.create_addon_structure("stock") as paths:
            addon_name = _extract_addon_name(paths["tests_dir"])
            self.assertEqual(addon_name, "stock")

    def test_extract_addon_name_with_pytest_node_id(self):
        """Test extracting addon name from pytest node ID (path with ::)."""
        with self.create_addon_structure("crm") as paths:
            # Simulate pytest node ID like: path/to/test.py::TestClass::test_method
            # We need to test the logic that splits on '::'
            # The actual split happens in pytest_cmdline_main,
            # but we can test the extraction
            addon_name = _extract_addon_name(paths["test_file"])
            self.assertEqual(addon_name, "crm")

    def test_extract_addon_name_no_manifest(self):
        """Test that None is returned when no __manifest__.py exists."""
        with tempfile.TemporaryDirectory() as temp_dir:
            some_path = Path(temp_dir) / "random" / "path"
            some_path.mkdir(parents=True, exist_ok=True)
            addon_name = _extract_addon_name(some_path)
            self.assertIsNone(addon_name)

    def test_extract_addon_name_multiple_levels(self):
        """Test extracting addon name from deeply nested path."""
        with self.create_addon_structure("account") as paths:
            # Create a deeply nested file
            deep_path = paths["tests_dir"] / "subfolder" / "deep" / "test_deep.py"
            deep_path.parent.mkdir(parents=True, exist_ok=True)
            deep_path.touch()

            addon_name = _extract_addon_name(deep_path)
            self.assertEqual(addon_name, "account")


class TestGetOdooVersion(TestCase):
    def test_get_odoo_version_returns_tuple(self):
        """Test that get_odoo_version returns a tuple."""
        version = get_odoo_version()
        self.assertIsInstance(version, tuple)
        self.assertGreaterEqual(len(version), 2)

    def test_get_odoo_version_with_version_info(self):
        """Test get_odoo_version when odoo.release.version_info exists."""
        import odoo

        if hasattr(odoo, "release") and hasattr(odoo.release, "version_info"):
            version = get_odoo_version()
            self.assertEqual(version, odoo.release.version_info)
        else:
            self.skipTest("odoo.release.version_info not available in test environment")

    def test_get_odoo_version_without_version_info(self):
        """Test get_odoo_version when odoo.release.version_info doesn't exist."""
        import odoo

        if not hasattr(odoo, "release"):
            version = get_odoo_version()
            self.assertEqual(version, (999, 0, 0, "final", 0, ""))
            return

        original_version_info = None
        has_version_info = hasattr(odoo.release, "version_info")
        if has_version_info:
            original_version_info = odoo.release.version_info

        def restore_version_info():
            if has_version_info:
                odoo.release.version_info = original_version_info

        self.addCleanup(restore_version_info)

        if has_version_info:
            del odoo.release.version_info

        version = get_odoo_version()
        self.assertEqual(version, (999, 0, 0, "final", 0, ""))

    def test_get_odoo_version_comparison(self):
        """Test that get_odoo_version result can be compared with tuples."""
        version = get_odoo_version()

        self.assertTrue(version < (1000,))
        self.assertTrue(version >= (0,))

        self.assertIsInstance(version[0], int)


class TestOptionValidation(TestCase):
    def test_find_unknown_odoo_options_detects_invalid_db_option(self):
        parser = SimpleNamespace(
            _long_opt={
                "--database": object(),
                "--db_maxconn": object(),
                "--workers": object(),
            },
            _short_opt={},
        )

        with patch("odoo.tools.config.parser", parser):
            unknown = _find_unknown_odoo_options(
                ["--database=test", "--db-maxconn=64", "--workers=4"]
            )

        self.assertEqual(unknown, ["--db-maxconn"])

    def test_validate_generated_odoo_options_has_actionable_message(self):
        parser = SimpleNamespace(
            _long_opt={"--database": object(), "--db_maxconn": object()},
            _short_opt={},
        )

        with patch("odoo.tools.config.parser", parser):
            with pytest.raises(pytest.UsageError) as exc_info:
                _validate_generated_odoo_options(
                    ["--database=test", "--db-maxconn=64"],
                    "/tmp/.oduit.toml",
                )

        message = str(exc_info.value)
        self.assertIn("/tmp/.oduit.toml", message)
        self.assertIn("--db-maxconn", message)
        self.assertIn("--db_maxconn", message)


class TestPluginAutoloadIsolation(TestCase):
    def test_plain_pytest_run_is_inert_without_oduit_config(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            (project / "test_plain.py").write_text(
                "def test_plain():\n    assert True\n"
            )

            env = os.environ.copy()
            repo_root = Path(__file__).resolve().parents[1]
            env["PYTHONPATH"] = str(repo_root)
            env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"

            result = subprocess.run(
                [sys.executable, "-m", "pytest", "-q", "-p", "pytest_oduit"],
                cwd=project,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("1 passed", result.stdout)

    def test_active_run_without_odoo_fails_with_clear_usage_error(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            (project / "test_plain.py").write_text(
                "def test_plain():\n    assert True\n"
            )
            (project / ".oduit.toml").write_text("[]\n")

            env = os.environ.copy()
            repo_root = Path(__file__).resolve().parents[1]
            env["PYTHONPATH"] = str(repo_root)
            env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
            block_odoo_runner = textwrap.dedent(
                """
                import importlib.abc
                import pytest
                import sys

                class BlockOdoo(importlib.abc.MetaPathFinder):
                    def find_spec(self, fullname, path=None, target=None):
                        if fullname == "odoo" or fullname.startswith("odoo."):
                            raise ModuleNotFoundError("No module named 'odoo'")
                        return None

                sys.meta_path.insert(0, BlockOdoo())
                raise SystemExit(pytest.main(["-q", "-p", "pytest_oduit"]))
                """
            )
            result = subprocess.run(
                [sys.executable, "-c", block_odoo_runner],
                cwd=project,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertNotEqual(result.returncode, 0)
            output = result.stdout + result.stderr
            self.assertIn("pytest-oduit detected an Odoo/oduit test run", output)
            self.assertIn("odoo", output)
