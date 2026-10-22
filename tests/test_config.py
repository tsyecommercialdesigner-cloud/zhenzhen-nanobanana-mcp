import os
import sys
import tempfile
import types
import unittest
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

from zhenzhen_nanobanana_mcp.config import (
    API_KEY_FIELD,
    BusinessError,
    Settings,
    load_api_key,
    read_windows_user_value,
)


class CredentialTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="nanobanana-config-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.env = self.root / ".env"
        self.environ = patch.dict(
            os.environ, {"NANOBANANA_PROJECT_DIR": str(self.root)}, clear=True
        )
        self.environ.start()
        self.addCleanup(self.environ.stop)
        self.registry = patch(
            "zhenzhen_nanobanana_mcp.config.read_windows_user_value", return_value=None
        )
        self.registry_mock = self.registry.start()
        self.addCleanup(self.registry.stop)

    def write(self, value):
        self.env.write_text(value, encoding="utf-8")

    def test_file_wins_and_process_environment_not_modified(self):
        self.write(
            "# private test fixture\nZHENZHEN_NANOBANANA_API_KEY='file-not-real' # comment\n"
        )
        os.environ[API_KEY_FIELD] = "process-not-real"
        self.registry_mock.return_value = "registry-not-real"
        settings = Settings.from_env()
        self.assertEqual(settings.api_key, "file-not-real")
        self.assertEqual(os.environ[API_KEY_FIELD], "process-not-real")
        self.registry_mock.assert_not_called()
        self.assertNotIn(settings.api_key, repr(settings))

    def test_field_absent_and_file_absent_fall_back(self):
        os.environ[API_KEY_FIELD] = "process-not-real"
        self.assertEqual(load_api_key(self.root), "process-not-real")
        self.write("OTHER_FIELD=example\n")
        self.assertEqual(load_api_key(self.root), "process-not-real")
        self.registry_mock.assert_not_called()

    def test_windows_user_fallback_only_when_process_field_absent(self):
        self.registry_mock.return_value = "registry-not-real"
        self.assertEqual(load_api_key(self.root), "registry-not-real")
        os.environ[API_KEY_FIELD] = ""
        with self.assertRaises(BusinessError):
            load_api_key(self.root)
        self.assertEqual(self.registry_mock.call_count, 1)

    def test_legacy_key_is_not_a_credential_source(self):
        self.assertEqual(API_KEY_FIELD, "ZHENZHEN_NANOBANANA_API_KEY")
        self.write("NANOBANANA_API_KEY=legacy-file-not-real\n")
        os.environ["NANOBANANA_API_KEY"] = "legacy-process-not-real"
        with self.assertRaisesRegex(BusinessError, API_KEY_FIELD):
            load_api_key(self.root)
        self.registry_mock.assert_called_once_with()
        os.environ[API_KEY_FIELD] = "new-process-not-real"
        self.assertEqual(load_api_key(self.root), "new-process-not-real")

    def test_empty_or_invalid_file_never_falls_back(self):
        os.environ[API_KEY_FIELD] = "old-process-not-real"
        for content in (
            "ZHENZHEN_NANOBANANA_API_KEY=\n",
            "ZHENZHEN_NANOBANANA_API_KEY='   '\n",
            "ZHENZHEN_NANOBANANA_API_KEY\n",
            "ZHENZHEN_NANOBANANA_API_KEY=Bearer fake\n",
            "ZHENZHEN_NANOBANANA_API_KEY='fake key'\n",
            'ZHENZHEN_NANOBANANA_API_KEY="fake\\nkey"\n',
        ):
            with self.subTest(content=content):
                self.write(content)
                with self.assertRaises(BusinessError) as raised:
                    load_api_key(self.root)
                self.assertNotIn("old-process-not-real", str(raised.exception))
        self.registry_mock.assert_not_called()

    def test_duplicate_and_syntax_errors_are_sanitized(self):
        os.environ[API_KEY_FIELD] = "old-process-not-real"
        for content in (
            "ZHENZHEN_NANOBANANA_API_KEY=first-not-real\nZHENZHEN_NANOBANANA_API_KEY=second-not-real\n",
            "ZHENZHEN_NANOBANANA_API_KEY=first-not-real\nBROKEN='second-not-real\n",
        ):
            self.write(content)
            with self.assertRaises(BusinessError) as raised:
                load_api_key(self.root)
            self.assertNotIn("first-not-real", str(raised.exception))
            self.assertNotIn("second-not-real", str(raised.exception))
        self.registry_mock.assert_not_called()

    def test_unreadable_and_invalid_encoding_do_not_fall_back(self):
        os.environ[API_KEY_FIELD] = "old-process-not-real"
        with patch.object(Path, "open", side_effect=PermissionError("secret-content")):
            with self.assertRaises(BusinessError) as raised:
                load_api_key(self.root)
            self.assertNotIn("secret-content", str(raised.exception))
            self.assertTrue(raised.exception.__suppress_context__)
        self.env.write_bytes(b"\xff\xffprivate-not-real")
        with self.assertRaises(BusinessError):
            load_api_key(self.root)
        self.registry_mock.assert_not_called()

    def test_literal_variables_and_special_characters(self):
        self.write('ZHENZHEN_NANOBANANA_API_KEY="${OTHER_KEY}#$(command)"\n')
        os.environ["OTHER_KEY"] = "must-not-expand"
        self.assertEqual(load_api_key(self.root), "${OTHER_KEY}#$(command)")
        self.env.write_bytes(b"\xef\xbb\xbfZHENZHEN_NANOBANANA_API_KEY=example#literal\n")
        self.assertEqual(load_api_key(self.root), "example#literal")

    def test_missing_and_invalid_compatible_sources_fail(self):
        with self.assertRaises(BusinessError):
            Settings.from_env()
        for key in ("", " ", "Bearer example", "example\n", "nonascii-密钥"):
            os.environ[API_KEY_FIELD] = key
            with self.assertRaises(BusinessError):
                load_api_key(self.root)
        os.environ.pop(API_KEY_FIELD)
        self.registry_mock.return_value = ""
        with self.assertRaises(BusinessError):
            load_api_key(self.root)

    def test_root_independent_of_cwd_no_search_or_environment_writes(self):
        self.write("ZHENZHEN_NANOBANANA_API_KEY=root-not-real\n")
        unrelated = self.root / "host-directory"
        unrelated.mkdir()
        (unrelated / ".env").write_text("ZHENZHEN_NANOBANANA_API_KEY=\n", encoding="utf-8")
        previous = Path.cwd()
        try:
            os.chdir(unrelated)
            result = Settings.from_env()
            self.assertEqual(result.api_key, "root-not-real")
            self.assertEqual(result.input_dirs, ())
        finally:
            os.chdir(previous)
        self.assertNotIn(API_KEY_FIELD, os.environ)

    def test_old_input_allowlist_is_ignored(self):
        self.write("ZHENZHEN_NANOBANANA_API_KEY=test-not-real\n")
        self.assertEqual(Settings.from_env().input_dirs, ())
        dirs = (self.root / "商品素材", self.root / "outputs")
        os.environ["NANOBANANA_INPUT_DIRS"] = os.pathsep.join(map(str, dirs))
        self.assertEqual(Settings.from_env().input_dirs, ())
        for value in ("", " ", "relative", str(dirs[0]) + os.pathsep):
            os.environ["NANOBANANA_INPUT_DIRS"] = value
            self.assertEqual(Settings.from_env().input_dirs, ())

    def test_task_queue_configuration_bounds_and_defaults(self):
        self.write("ZHENZHEN_NANOBANANA_API_KEY=test-not-real\n")
        defaults = Settings.from_env()
        self.assertEqual((defaults.concurrency, defaults.max_pending_tasks), (5, 200))
        for key, valid, invalid in (
            ("NANOBANANA_CONCURRENCY", ("1", "5", "20"), ("0", "21", "1.5", "")),
            ("NANOBANANA_MAX_PENDING_TASKS", ("20", "200", "1000"), ("19", "1001", "NaN", "")),
        ):
            for value in valid:
                with patch.dict(os.environ, {key: value}):
                    Settings.from_env()
            for value in invalid:
                with self.subTest(key=key, value=value), patch.dict(os.environ, {key: value}):
                    with self.assertRaises(BusinessError):
                        Settings.from_env()

    def test_registry_adapter_uses_hkcu_read_only_and_raw_strings(self):
        self.registry.stop()
        mock = types.ModuleType("winreg")
        mock.HKEY_CURRENT_USER, mock.KEY_READ, mock.REG_SZ, mock.REG_EXPAND_SZ = 1, 2, 3, 4
        mock.OpenKey = MagicMock()
        mock.QueryValueEx = MagicMock(return_value=("registry-not-real", mock.REG_SZ))
        with patch.dict(sys.modules, {"winreg": mock}), patch("sys.platform", "win32"):
            self.assertEqual(read_windows_user_value(), "registry-not-real")
            mock.OpenKey.assert_called_with(mock.HKEY_CURRENT_USER, "Environment", 0, mock.KEY_READ)
            mock.QueryValueEx.assert_called_with(
                mock.OpenKey.return_value.__enter__.return_value,
                "ZHENZHEN_NANOBANANA_API_KEY",
            )
            mock.QueryValueEx.return_value = (42, 5)
            with self.assertRaises(BusinessError):
                read_windows_user_value()
            mock.QueryValueEx.side_effect = PermissionError("registry-secret")
            with self.assertRaises(BusinessError) as raised:
                read_windows_user_value()
            self.assertNotIn("registry-secret", str(raised.exception))

    @unittest.skipUnless(sys.platform == "win32", "Windows current-user registry only")
    def test_real_current_user_registry_missing_field_read(self):
        self.registry.stop()
        self.assertIsNone(read_windows_user_value("NANOBANANA_TEST_" + uuid.uuid4().hex))

    def test_non_windows_does_not_query_registry(self):
        self.registry.stop()
        with patch("sys.platform", "linux"):
            self.assertIsNone(read_windows_user_value())


if __name__ == "__main__":
    unittest.main()
