#!/usr/bin/env python3
"""Refreshable, read-only Kubernetes resource overview using the Python client.

Examples:
    python k1s.py
    python k1s.py --namespace kube-system --resource pods
    python k1s.py --all-namespaces --resource pods --resource services --once
    python k1s.py --resource all --details --interval 2
"""

from __future__ import annotations

import argparse
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
import os
import sys
import time

from kubernetes import client
from kubernetes.client.exceptions import ApiException

from common.common import (
    ClusterContext,
    colorize,
    load_kubernetes_config,
    render_table,
)

DEFAULT_RESOURCES = ("pods",)


@dataclass(frozen=True, slots=True)
class DisplayRow:
    """One resource row and its numeric age, used for stable age sorting."""

    age_seconds: int
    values: tuple[str, ...]


def format_age(created: datetime | None, *, now: datetime | None = None) -> tuple[int, str]:
    """Return elapsed seconds and a kubectl-style age from a creation timestamp.

    The API returns UTC timestamps. Naive timestamps are therefore interpreted
    as UTC rather than as the machine's local timezone. Aware datetime
    arithmetic avoids local-time conversion errors; explicit divmod also avoids
    corrupting age strings with strip('0').
    """
    if created is None:
        return 0, "-"
    if created.tzinfo is None:
        created = created.replace(tzinfo=UTC)
    else:
        created = created.astimezone(UTC)

    current = now or datetime.now(UTC)
    if current.tzinfo is None:
        current = current.replace(tzinfo=UTC)
    else:
        current = current.astimezone(UTC)

    seconds = max(0, int((current - created).total_seconds()))
    days, remainder = divmod(seconds, 86_400)
    hours, remainder = divmod(remainder, 3_600)
    minutes, secs = divmod(remainder, 60)

    if days:
        age = f"{days}d{hours}h{minutes:02d}m"
    elif hours:
        age = f"{hours}h{minutes:02d}m{secs:02d}s"
    elif minutes:
        age = f"{minutes}m{secs:02d}s"
    else:
        age = f"{secs}s"
    return seconds, age


def _container_images(template: client.V1PodTemplateSpec | None) -> str:
    if template is None or template.spec is None:
        return "-"
    images = [
        container.image
        for container in template.spec.containers or []
        if container.image
    ]
    return ", ".join(images) or "-"


def _ready_pods(pod: client.V1Pod) -> str:
    expected = len(pod.spec.containers or []) if pod.spec else 0
    ready = (
        sum(1 for status in (pod.status.container_statuses or []) if status.ready)
        if pod.status
        else 0
    )
    return f"{ready}/{expected}"


def _pod_status(pod: client.V1Pod) -> str:
    if pod.metadata.deletion_timestamp:
        return "Terminating"
    if pod.status is None:
        return "Unknown"
    for container_status in pod.status.container_statuses or []:
        state = container_status.state
        if state and state.waiting and state.waiting.reason:
            return state.waiting.reason
        if state and state.terminated and state.terminated.reason:
            return state.terminated.reason
    return pod.status.phase or "Unknown"


def _fetch_resources(
    core: client.CoreV1Api,
    apps: client.AppsV1Api,
    batch: client.BatchV1Api,
    resource: str,
    namespace: str,
) -> list[DisplayRow]:
    """Fetch and normalize one supported resource type."""
    all_namespaces = namespace == "all"
    rows: list[DisplayRow] = []

    def add(
        metadata: client.V1ObjectMeta,
        kind: str,
        *,
        ready: str = "-",
        status: str = "-",
        details: str = "-",
    ) -> None:
        age_seconds, age = format_age(metadata.creation_timestamp)
        rows.append(
            DisplayRow(
                age_seconds,
                (
                    metadata.namespace or "-",
                    kind,
                    metadata.name or "-",
                    ready,
                    status,
                    age,
                    details,
                ),
            )
        )

    if resource in {"all", "nodes"}:
        for node in core.list_node().items:
            status = node.status
            internal_ip = next(
                (
                    address.address
                    for address in (status.addresses or [])
                    if address.type == "InternalIP"
                ),
                "-",
            )
            ready = next(
                (
                    condition.status
                    for condition in (status.conditions or [])
                    if condition.type == "Ready"
                ),
                "Unknown",
            )
            version = status.node_info.kubelet_version if status.node_info else "-"
            node_status = "Cordoned" if node.spec.unschedulable else ready
            add(
                node.metadata,
                "Node",
                ready=ready,
                status=node_status,
                details=f"IP={internal_ip} kubelet={version}",
            )

    if resource in {"all", "pods"}:
        result = (
            core.list_pod_for_all_namespaces()
            if all_namespaces
            else core.list_namespaced_pod(namespace=namespace)
        )
        for pod in result.items:
            status = pod.status
            pod_ip = status.pod_ip if status else None
            host_ip = status.host_ip if status else None
            node_name = pod.spec.node_name if pod.spec else None
            images = _container_images(
                client.V1PodTemplateSpec(spec=pod.spec) if pod.spec else None
            )
            details = (
                f"podIP={pod_ip or '-'} hostIP={host_ip or '-'} "
                f"node={node_name or '-'} images={images}"
            )
            add(
                pod.metadata,
                "Pod",
                ready=_ready_pods(pod),
                status=_pod_status(pod),
                details=details,
            )

    if resource in {"all", "deployments"}:
        result = (
            apps.list_deployment_for_all_namespaces()
            if all_namespaces
            else apps.list_namespaced_deployment(namespace=namespace)
        )
        for item in result.items:
            desired = item.spec.replicas or 0
            actual = item.status.ready_replicas or 0
            conditions = item.status.conditions or []
            status = conditions[-1].type if conditions else "Unknown"
            add(
                item.metadata,
                "Deployment",
                ready=f"{actual}/{desired}",
                status=status,
                details=f"images={_container_images(item.spec.template)}",
            )

    if resource in {"all", "daemonsets"}:
        result = (
            apps.list_daemon_set_for_all_namespaces()
            if all_namespaces
            else apps.list_namespaced_daemon_set(namespace=namespace)
        )
        for item in result.items:
            desired = item.status.desired_number_scheduled or 0
            actual = item.status.number_ready or 0
            add(
                item.metadata,
                "DaemonSet",
                ready=f"{actual}/{desired}",
                details=f"images={_container_images(item.spec.template)}",
            )

    if resource in {"all", "statefulsets"}:
        result = (
            apps.list_stateful_set_for_all_namespaces()
            if all_namespaces
            else apps.list_namespaced_stateful_set(namespace=namespace)
        )
        for item in result.items:
            desired = item.spec.replicas or 0
            actual = item.status.ready_replicas or 0
            add(
                item.metadata,
                "StatefulSet",
                ready=f"{actual}/{desired}",
                details=f"images={_container_images(item.spec.template)}",
            )

    if resource in {"all", "replicasets"}:
        result = (
            apps.list_replica_set_for_all_namespaces()
            if all_namespaces
            else apps.list_namespaced_replica_set(namespace=namespace)
        )
        for item in result.items:
            desired = item.spec.replicas or 0
            actual = item.status.ready_replicas or 0
            add(
                item.metadata,
                "ReplicaSet",
                ready=f"{actual}/{desired}",
                details=f"images={_container_images(item.spec.template)}",
            )

    if resource in {"all", "services"}:
        result = (
            core.list_service_for_all_namespaces()
            if all_namespaces
            else core.list_namespaced_service(namespace=namespace)
        )
        for item in result.items:
            ports = ",".join(
                f"{port.port}/{port.protocol or 'TCP'}"
                for port in item.spec.ports or []
            ) or "-"
            add(
                item.metadata,
                "Service",
                status=item.spec.type or "Unknown",
                details=f"clusterIP={item.spec.cluster_ip or '-'} ports={ports}",
            )

    if resource in {"all", "jobs"}:
        result = (
            batch.list_job_for_all_namespaces()
            if all_namespaces
            else batch.list_namespaced_job(namespace=namespace)
        )
        for item in result.items:
            desired = item.spec.completions or 1
            succeeded = item.status.succeeded or 0
            active = item.status.active or 0
            add(
                item.metadata,
                "Job",
                ready=f"{succeeded}/{desired}",
                status=f"active={active}",
                details=f"images={_container_images(item.spec.template)}",
            )

    if resource in {"all", "cronjobs"}:
        result = (
            batch.list_cron_job_for_all_namespaces()
            if all_namespaces
            else batch.list_namespaced_cron_job(namespace=namespace)
        )
        for item in result.items:
            active = len(item.status.active or [])
            add(
                item.metadata,
                "CronJob",
                ready=f"active={active}",
                status="Suspended" if item.spec.suspend else "Scheduled",
                details=(
                    f"schedule={item.spec.schedule} "
                    f"images={_container_images(item.spec.job_template.spec.template)}"
                ),
            )

    if resource in {"all", "pvs"}:
        for item in core.list_persistent_volume().items:
            capacity = (item.spec.capacity or {}).get("storage", "-")
            add(
                item.metadata,
                "PV",
                status=item.status.phase or "Unknown",
                details=f"capacity={capacity} access={','.join(item.spec.access_modes or [])}",
            )

    if resource in {"all", "pvcs"}:
        result = (
            core.list_persistent_volume_claim_for_all_namespaces()
            if all_namespaces
            else core.list_namespaced_persistent_volume_claim(namespace=namespace)
        )
        for item in result.items:
            capacity = (item.status.capacity or {}).get("storage", "-")
            add(
                item.metadata,
                "PVC",
                status=item.status.phase or "Unknown",
                details=f"capacity={capacity} class={item.spec.storage_class_name or '-'}",
            )

    return sorted(rows, key=lambda row: row.age_seconds, reverse=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    scope = parser.add_mutually_exclusive_group()
    scope.add_argument("-A", "--all-namespaces", action="store_true")
    scope.add_argument("-n", "--namespace", help="Namespace (default: context namespace).")
    parser.add_argument(
        "-r",
        "--resource",
        action="append",
        choices=(
            "all",
            "nodes",
            "pods",
            "deployments",
            "daemonsets",
            "statefulsets",
            "replicasets",
            "services",
            "jobs",
            "cronjobs",
            "pvs",
            "pvcs",
        ),
        help="Resource type to show; repeat to combine. Defaults to Pods.",
    )
    parser.add_argument(
        "--details",
        action="store_true",
        help="Show extended details such as Pod IPs, node names, images, and service ports.",
    )
    parser.add_argument(
        "--color",
        choices=("auto", "always", "never"),
        default="auto",
        help="Color healthy, waiting, and failed states (default: auto for terminals).",
    )
    parser.add_argument(
        "--once", action="store_true", help="Render once instead of refreshing continuously."
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=2.0,
        help="Refresh interval in seconds (default: 2; must be positive).",
    )
    return parser


def _collect(
    core: client.CoreV1Api,
    apps: client.AppsV1Api,
    batch: client.BatchV1Api,
    resources: Iterable[str],
    namespace: str,
) -> list[DisplayRow]:
    """Collect selected resources and avoid duplicates in combined selections."""
    rows: list[DisplayRow] = []
    for resource in resources:
        rows.extend(_fetch_resources(core, apps, batch, resource, namespace))
    unique = {row.values[:3]: row for row in rows}
    return sorted(unique.values(), key=lambda row: row.age_seconds, reverse=True)


def _render(
    rows: Sequence[DisplayRow],
    context: ClusterContext,
    namespace: str,
    *,
    details: bool = False,
    color: bool = False,
) -> str:
    """Render a short demo-friendly table; expose diagnostic columns on request."""
    if details:
        headers = ("NAMESPACE", "TYPE", "NAME", "READY", "STATUS", "AGE", "DETAILS")
    else:
        headers = ("NAMESPACE", "TYPE", "NAME", "READY", "STATUS", "AGE")

    values = (
        _color_row(row.values, enabled=color)[: len(headers)]
        for row in rows
    )
    table = render_table(headers, values)
    return f"Context: {context.name} / Namespace: {namespace}\n\n{table}"


def _color_for_status(status: str) -> str | None:
    """Choose a semantic color for a Kubernetes state label."""
    normalized = status.casefold()
    if normalized in {"running", "ready", "succeeded", "complete", "available", "healthy", "true"}:
        return "32"  # green
    if normalized in {
        "failed",
        "error",
        "terminating",
        "crashloopbackoff",
        "imagepullbackoff",
        "errimagepull",
        "createcontainerconfigerror",
        "invalidimagename",
        "false",
    }:
        return "31"  # red
    if normalized in {
        "pending",
        "unknown",
        "progressing",
        "containercreating",
        "podinitializing",
        "cordoned",
        "suspended",
        "scheduled",
    }:
        return "33"  # yellow
    return None


def _color_for_readiness(ready: str) -> str | None:
    """Color replica/container readiness ratios without changing their text."""
    current, separator, desired = ready.partition("/")
    if not separator or not current.isdigit() or not desired.isdigit() or desired == "0":
        return None
    if int(current) >= int(desired):
        return "32"
    if int(current) == 0:
        return "31"
    return "33"


def _color_row(values: tuple[str, ...], *, enabled: bool) -> tuple[str, ...]:
    """Apply semantic colors to READY and STATUS cells only."""
    mutable = list(values)
    if enabled:
        ready_color = _color_for_readiness(mutable[3])
        status_color = _color_for_status(mutable[4])
        if ready_color:
            mutable[3] = colorize(mutable[3], ready_color, enabled=True)
        if status_color:
            mutable[4] = colorize(mutable[4], status_color, enabled=True)
    return tuple(mutable)


def _color_enabled(mode: str) -> bool:
    """Resolve automatic color based on terminal/NO_COLOR conventions."""
    if mode == "always":
        return True
    if mode == "never" or "NO_COLOR" in os.environ:
        return False
    return sys.stdout.isatty()


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.interval <= 0:
        parser.error("--interval must be greater than zero.")

    try:
        context = load_kubernetes_config()
        namespace = "all" if args.all_namespaces else args.namespace or context.namespace
        resources = args.resource or list(DEFAULT_RESOURCES)
        core = client.CoreV1Api()
        apps = client.AppsV1Api()
        batch = client.BatchV1Api()

        while True:
            try:
                rows = _collect(core, apps, batch, resources, namespace)
            except ApiException as exc:
                parser.exit(1, f"Kubernetes API error ({exc.status}): {exc.reason}\n")
            output = _render(
                rows,
                context,
                namespace,
                details=args.details,
                color=_color_enabled(args.color),
            )
            if args.once:
                print(output)
                break
            sys.stdout.write("\033[2J\033[H")
            print(output, flush=True)
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nStopped.", file=sys.stderr)
    except RuntimeError as exc:
        parser.exit(1, f"{exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
