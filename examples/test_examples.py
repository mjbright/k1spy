"""Offline unit tests for formatting and Kubernetes quantity parsing."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import importlib.util
from pathlib import Path
import re
import unittest

from k1s import (
    DEFAULT_RESOURCES,
    DisplayRow,
    _render,
    _color_for_readiness,
    _color_for_status,
    format_age,
)
from common.common import ClusterContext, render_table

_QUANTITIES_PATH = Path(__file__).with_name("kubernetes-python_simple_req_limits.py")
_QUANTITIES_SPEC = importlib.util.spec_from_file_location(
    "resource_requests_limits", _QUANTITIES_PATH
)
assert _QUANTITIES_SPEC is not None and _QUANTITIES_SPEC.loader is not None
_QUANTITIES = importlib.util.module_from_spec(_QUANTITIES_SPEC)
_QUANTITIES_SPEC.loader.exec_module(_QUANTITIES)
parse_quantity = _QUANTITIES.parse_quantity


class AgeFormattingTests(unittest.TestCase):
    def test_three_minutes_and_five_seconds(self) -> None:
        now = datetime(2026, 10, 22, 12, 0, tzinfo=UTC)
        seconds, display = format_age(now - timedelta(minutes=3, seconds=5), now=now)
        self.assertEqual(seconds, 185)
        self.assertEqual(display, "3m05s")

    def test_hour_age_includes_minutes_and_seconds(self) -> None:
        now = datetime(2026, 10, 22, 12, 0, tzinfo=UTC)
        _, display = format_age(now - timedelta(hours=2, minutes=3, seconds=5), now=now)
        self.assertEqual(display, "2h03m05s")

    def test_naive_kubernetes_timestamp_is_treated_as_utc(self) -> None:
        created = datetime(2026, 10, 22, 11, 0, 0)
        now = datetime(2026, 10, 22, 12, 0, 0, tzinfo=UTC)
        self.assertEqual(format_age(created, now=now), (3600, "1h00m00s"))

    def test_future_creation_time_is_clamped(self) -> None:
        now = datetime(2026, 10, 22, 12, 0, tzinfo=UTC)
        self.assertEqual(format_age(now + timedelta(seconds=2), now=now), (0, "0s"))


class TableFormattingTests(unittest.TestCase):
    def test_all_fields_align_to_longest_value(self) -> None:
        table = render_table(
            ("POD", "IP", "IMAGE"),
            (("api", "10.0.0.10", "example/api:v1"), ("worker-long", "-", "repo/worker:v1")),
        )
        lines = table.splitlines()
        self.assertEqual(lines[0].index("IP"), lines[2].index("10.0.0.10"))
        self.assertEqual(lines[0].index("IMAGE"), lines[2].index("example/api:v1"))

    def test_ansi_color_codes_do_not_break_column_alignment(self) -> None:
        colored = render_table(
            ("READY", "STATUS", "AGE"),
            (("\033[32m1/1\033[0m", "\033[32mRunning\033[0m", "3m05s"), ("0/1", "Pending", "15s")),
        )
        lines = colored.splitlines()
        visible_lines = [re.sub(r"\033\[[0-9;]*m", "", line) for line in lines]
        self.assertEqual(visible_lines[0].index("STATUS"), visible_lines[2].index("Running"))
        self.assertEqual(visible_lines[0].index("AGE"), visible_lines[2].index("3m05s"))

    def test_rejects_row_with_wrong_column_count(self) -> None:
        with self.assertRaises(ValueError):
            render_table(("A", "B"), (("only one",),))

    def test_k1s_defaults_to_pods(self) -> None:
        self.assertEqual(DEFAULT_RESOURCES, ("pods",))

    def test_k1s_compact_view_hides_extended_details(self) -> None:
        row = DisplayRow(
            185,
            (
                "demo",
                "Pod",
                "api",
                "1/1",
                "Running",
                "3m05s",
                "image=busybox podIP=10.0.0.1",
            ),
        )
        compact = _render([row], ClusterContext("demo-context", "demo"), "demo")
        detailed = _render(
            [row], ClusterContext("demo-context", "demo"), "demo", details=True
        )

        self.assertIn("NAMESPACE  TYPE  NAME  READY  STATUS   AGE", compact)
        self.assertNotIn("DETAILS", compact)
        self.assertNotIn("podIP=10.0.0.1", compact)
        self.assertIn("podIP=10.0.0.1", detailed)
        colored = _render(
            [row], ClusterContext("demo-context", "demo"), "demo", color=True
        )
        self.assertIn("\033[32m1/1\033[0m", colored)
        self.assertIn("\033[32mRunning\033[0m", colored)

    def test_k1s_status_and_readiness_colors_are_semantic(self) -> None:
        self.assertEqual(_color_for_status("Running"), "32")
        self.assertEqual(_color_for_status("Pending"), "33")
        self.assertEqual(_color_for_status("Failed"), "31")
        self.assertEqual(_color_for_readiness("2/2"), "32")
        self.assertEqual(_color_for_readiness("1/2"), "33")
        self.assertEqual(_color_for_readiness("0/2"), "31")


class KubernetesQuantityTests(unittest.TestCase):
    def test_cpu_decimal_suffixes(self) -> None:
        from decimal import Decimal

        self.assertEqual(parse_quantity("500m"), Decimal("0.5"))
        self.assertEqual(parse_quantity("2"), Decimal("2"))
        self.assertEqual(parse_quantity("125u"), Decimal("0.000125"))

    def test_memory_binary_and_decimal_suffixes(self) -> None:
        from decimal import Decimal

        self.assertEqual(parse_quantity("1Gi"), Decimal(1024**3))
        self.assertEqual(parse_quantity("1G"), Decimal(10**9))
        self.assertEqual(parse_quantity("750Mi"), Decimal(750 * 1024**2))

    def test_rejects_unknown_suffix(self) -> None:
        with self.assertRaises(ValueError):
            parse_quantity("5widgets")

    def test_scientific_notation(self) -> None:
        from decimal import Decimal

        self.assertEqual(parse_quantity("1e3"), Decimal("1e3"))


if __name__ == "__main__":
    unittest.main()
