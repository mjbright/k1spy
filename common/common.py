"""Shared setup and formatting helpers for the Kubernetes examples."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
import os
import re

from kubernetes import config
from kubernetes.config.config_exception import ConfigException

_ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*m")


def colorize(value: str, ansi_code: str, *, enabled: bool) -> str:
    """Wrap a terminal value in ANSI color when enabled."""
    if not enabled:
        return value
    return f"\033[{ansi_code}m{value}\033[0m"


@dataclass(frozen=True, slots=True)
class ClusterContext:
    """The selected Kubernetes context and its default namespace."""

    name: str
    namespace: str


def load_kubernetes_config() -> ClusterContext:
    """Load in-cluster credentials or the user's current kubeconfig context.

    Kubernetes service environment variables are present in normal Pods. All
    other invocations use the standard kubeconfig resolution rules, including
    the KUBECONFIG environment variable and ~/.kube/config.
    """
    if os.environ.get("KUBERNETES_SERVICE_HOST"):
        config.load_incluster_config()
        return ClusterContext(name="in-cluster", namespace="default")

    try:
        config.load_kube_config()
    except ConfigException as exc:
        raise RuntimeError(
            "Could not load Kubernetes credentials. Configure ~/.kube/config "
            "or run this script from a Pod with a ServiceAccount."
        ) from exc

    contexts, active_context = config.list_kube_config_contexts()
    if not contexts or active_context is None:
        return ClusterContext(name="unknown", namespace="default")

    selected = active_context.get("context", {})
    return ClusterContext(
        name=active_context.get("name", "unknown"),
        namespace=selected.get("namespace", "default"),
    )


def render_table(
    headers: Sequence[str],
    rows: Iterable[Sequence[object]],
    *,
    min_widths: Sequence[int] | None = None,
) -> str:
    """Render a small plain-text table, measuring every field consistently."""
    materialized_rows = [tuple(str(value) for value in row) for row in rows]
    if any(len(row) != len(headers) for row in materialized_rows):
        raise ValueError("Every table row must have the same number of fields as headers.")

    visible_length = lambda value: len(_ANSI_ESCAPE.sub("", value))
    widths = [visible_length(header) for header in headers]
    for row in materialized_rows:
        widths = [
            max(width, visible_length(value))
            for width, value in zip(widths, row, strict=True)
        ]
    if min_widths is not None:
        if len(min_widths) != len(headers):
            raise ValueError("min_widths must have one entry per header.")
        widths = [max(width, minimum) for width, minimum in zip(widths, min_widths, strict=True)]

    def format_row(values: Sequence[str]) -> str:
        return "  ".join(
            value + " " * max(0, width - visible_length(value))
            for value, width in zip(values, widths, strict=True)
        ).rstrip()

    lines = [format_row(headers), format_row(tuple("-" * width for width in widths))]
    lines.extend(format_row(row) for row in materialized_rows)
    return "\n".join(lines)
