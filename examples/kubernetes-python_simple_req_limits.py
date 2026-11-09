#!/usr/bin/env python3
"""Summarize container CPU and memory requests/limits by namespace and node.

This example sums ordinary application-container values. Kubernetes scheduling
also accounts for init-container maxima, Pod overhead, and admission defaults;
those are intentionally outside this lightweight report's scope.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from decimal import Decimal
from typing import NamedTuple

from kubernetes import client
from kubernetes.client.exceptions import ApiException
from kubernetes.utils.quantity import parse_quantity as parse_kubernetes_quantity

from common.common import load_kubernetes_config


class Totals(NamedTuple):
    request_cpu: Decimal
    limit_cpu: Decimal
    request_memory: Decimal
    limit_memory: Decimal


def parse_quantity(value: str | None) -> Decimal:
    """Convert a Kubernetes quantity using the official client quantity parser.

    The base unit is defined by the caller: cores for CPU and bytes for memory.
    """
    if not value:
        return Decimal(0)
    try:
        return parse_kubernetes_quantity(value)
    except (ValueError, ArithmeticError) as exc:
        raise ValueError(f"Invalid Kubernetes quantity: {value!r}") from exc


def empty_totals() -> dict[str, Decimal]:
    return {
        "request_cpu": Decimal(0),
        "limit_cpu": Decimal(0),
        "request_memory": Decimal(0),
        "limit_memory": Decimal(0),
    }


def add_container_resources(
    totals: dict[str, Decimal], resources: client.V1ResourceRequirements | None
) -> None:
    """Accumulate one container's CPU and memory resource values."""
    if resources is None:
        return
    requests = resources.requests or {}
    limits = resources.limits or {}

    totals["request_cpu"] += parse_quantity(requests.get("cpu"))
    totals["limit_cpu"] += parse_quantity(limits.get("cpu"))
    totals["request_memory"] += parse_quantity(requests.get("memory"))
    totals["limit_memory"] += parse_quantity(limits.get("memory"))


def human_bytes(value: Decimal) -> str:
    """Format bytes using binary units while keeping the underlying value exact."""
    units = ("B", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei")
    amount = value
    for unit in units:
        if abs(amount) < 1024 or unit == units[-1]:
            return f"{amount.quantize(Decimal('0.1')):,.1f} {unit}"
        amount /= 1024
    return f"{amount:,.1f} Ei"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    scope = parser.add_mutually_exclusive_group()
    scope.add_argument("-A", "--all-namespaces", action="store_true")
    scope.add_argument("-n", "--namespace", help="Namespace to summarize.")
    parser.add_argument(
        "-d", "--details", action="store_true", help="Print per-container resource settings."
    )
    args = parser.parse_args()

    try:
        context = load_kubernetes_config()
        core = client.CoreV1Api()
        nodes = core.list_node().items
        if args.all_namespaces:
            pods = core.list_pod_for_all_namespaces().items
            namespaces = sorted(
                {pod.metadata.namespace for pod in pods if pod.metadata.namespace}
            )
        else:
            namespace = args.namespace or context.namespace
            pods = core.list_namespaced_pod(namespace=namespace).items
            namespaces = [namespace]
    except (RuntimeError, ApiException) as exc:
        parser.exit(1, f"Unable to summarize resources: {exc}\n")

    by_node: defaultdict[str, dict[str, Decimal]] = defaultdict(empty_totals)
    by_namespace: defaultdict[str, dict[str, Decimal]] = defaultdict(empty_totals)

    if args.details:
        print(f"Context: {context.name}")

    for pod in pods:
        namespace = pod.metadata.namespace or "unknown"
        node_name = pod.spec.node_name or "<unscheduled>"
        for container in pod.spec.containers or []:
            resources = container.resources
            add_container_resources(by_namespace[namespace], resources)
            if pod.spec.node_name:
                add_container_resources(by_node[node_name], resources)
            if args.details:
                print(f"{node_name}  {namespace}/{pod.metadata.name}  {container.name}")
                print(f"  requests={resources.requests if resources else None}")
                print(f"  limits={resources.limits if resources else None}")

    def print_summary(label: str, values: dict[str, Decimal]) -> None:
        print(
            f"{label:25}  "
            f"request CPU {values['request_cpu']:>9.3f} cores  "
            f"limit CPU {values['limit_cpu']:>9.3f} cores  "
            f"request memory {human_bytes(values['request_memory']):>10}  "
            f"limit memory {human_bytes(values['limit_memory']):>10}"
        )

    print(f"Namespace totals (context: {context.name})")
    for namespace in namespaces:
        print_summary(namespace, by_namespace[namespace])
    print("\nNode totals (unscheduled Pods are excluded)")
    for node in nodes:
        name = node.metadata.name
        print_summary(name, by_node[name])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
