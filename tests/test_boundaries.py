import importlib
import unittest
from unittest.mock import patch
from everyday.common import PLUGINS, ConfigurationError, NoRedirect, clock, packet, push, request


class BoundaryTests(unittest.TestCase):
    def test_all_seven_demos_fit_and_cannot_be_published(self):
        self.assertEqual(len(PLUGINS), 7)
        for slug in PLUGINS:
            with self.subTest(plugin=slug):
                data = importlib.import_module(f"everyday.{slug}").demo(clock({}))
                self.assertLessEqual(len(packet(data)), 2000)
                with patch("everyday.common.request") as network:
                    with self.assertRaises(ConfigurationError):
                        push(data)
                    network.assert_not_called()

    def test_destination_redirect_and_size_guards(self):
        for url in ("http://example.invalid", "https://user:password@example.invalid", "file:///etc/passwd"):
            with self.subTest(url=url), self.assertRaises(ConfigurationError):
                request(url)
        with self.assertRaises(ConfigurationError):
            NoRedirect().redirect_request(None, None, 302, "Found", {}, "https://example.invalid")
        with patch.dict("os.environ", {"TRMNL_WEBHOOK_URL": "https://example.invalid/api/custom_plugins/example"}):
            with patch("everyday.common.request") as network:
                with self.assertRaises(ConfigurationError):
                    push({"title": "Private"})
                network.assert_not_called()
        with self.assertRaises(ConfigurationError):
            packet({"title": "x" * 2000})
        with self.assertRaises(ValueError):
            packet({"value": float("nan")})


if __name__ == "__main__":
    unittest.main()
