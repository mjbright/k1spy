#!/usr/bin/env python3
"""Minimal example: list cluster nodes and Pods in one namespace."""

from __future__ import annotations

import argparse

from kubernetes import client
from kubernetes.client.exceptions import ApiException

from common.common import load_kubernetes_config, render_table


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-n", "--namespace", default=None)
    args = parser.parse_args()

    try:
        context = load_kubernetes_config()
        core = client.CoreV1Api()
        namespace = args.namespace or context.namespace
        nodes = core.list_node().items
        pods = core.list_namespaced_pod(namespace=namespace).items
    except (RuntimeError, ApiException) as exc:
        parser.exit(1, f"Unable to query the Kubernetes API: {exc}\n")

    print(f"Context: {context.name}")
    print("\nNodes")
    print(render_table(
        ("NAME", "INTERNAL IP", "KUBELET"),
        (
            (
                node.metadata.name or "-",
                next(
                    (
                        address.address
                        for address in (node.status.addresses or [])
                        if address.type == "InternalIP"
                    ),
                    "-",
                ),
                node.status.node_info.kubelet_version
                if node.status.node_info and node.status.node_info.kubelet_version
                else "-",
            )
            for node in nodes
        ),
    ))

    print(f"\nPods in namespace {namespace!r}")
    print(render_table(
        ("NAME", "PHASE", "NODE"),
        (
            (pod.metadata.name or "-", pod.status.phase or "-", pod.spec.node_name or "-")
            for pod in pods
        ),
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
