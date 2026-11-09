#!/usr/bin/env python3
"""List Pods and their node/pod IPs using the Kubernetes Python client."""

from __future__ import annotations

import argparse

from kubernetes import client
from kubernetes.client.exceptions import ApiException

from common.common import load_kubernetes_config, render_table


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-n",
        "--namespace",
        help="Namespace to list (default: all namespaces).",
    )
    args = parser.parse_args()

    try:
        context = load_kubernetes_config()
        core = client.CoreV1Api()
        if args.namespace:
            result = core.list_namespaced_pod(namespace=args.namespace)
        else:
            result = core.list_pod_for_all_namespaces()
    except (RuntimeError, ApiException) as exc:
        parser.exit(1, f"Unable to list Pods: {exc}\n")

    rows = [
        (
            pod.metadata.namespace or "-",
            pod.metadata.name or "-",
            pod.status.pod_ip or "-",
            pod.status.host_ip or "-",
            pod.spec.node_name or "-",
        )
        for pod in result.items
    ]
    print(f"Context: {context.name}")
    print(render_table(("NAMESPACE", "NAME", "POD IP", "HOST IP", "NODE"), rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
