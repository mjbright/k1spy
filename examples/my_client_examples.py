#!/usr/bin/env python3
"""Demonstrate common read-only Kubernetes API list calls.

This modernized version of the notebook-style original lists the common
resource types without shelling out to kubectl or running at import time.
"""

from __future__ import annotations

import argparse
from collections.abc import Iterable

from kubernetes import client
from kubernetes.client.exceptions import ApiException

from common.common import load_kubernetes_config, render_table


def _namespace_rows(items: Iterable[object]) -> list[tuple[str, str]]:
    return [
        (
            item.metadata.namespace or "-",
            item.metadata.name or "-",
        )
        for item in items
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    scope = parser.add_mutually_exclusive_group()
    scope.add_argument("-A", "--all-namespaces", action="store_true")
    scope.add_argument("-n", "--namespace", help="Namespace (default: all namespaces).")
    args = parser.parse_args()
    namespace = "all" if args.all_namespaces or not args.namespace else args.namespace

    try:
        context = load_kubernetes_config()
        core = client.CoreV1Api()
        apps = client.AppsV1Api()
        batch = client.BatchV1Api()

        def namespaced_list(all_method, namespaced_method):
            if namespace == "all":
                return all_method().items
            return namespaced_method(namespace=namespace).items

        resource_lists = (
            ("Pods", namespaced_list(core.list_pod_for_all_namespaces, core.list_namespaced_pod)),
            ("Services", namespaced_list(core.list_service_for_all_namespaces, core.list_namespaced_service)),
            (
                "Deployments",
                namespaced_list(
                    apps.list_deployment_for_all_namespaces,
                    apps.list_namespaced_deployment,
                ),
            ),
            (
                "DaemonSets",
                namespaced_list(
                    apps.list_daemon_set_for_all_namespaces,
                    apps.list_namespaced_daemon_set,
                ),
            ),
            (
                "ReplicaSets",
                namespaced_list(
                    apps.list_replica_set_for_all_namespaces,
                    apps.list_namespaced_replica_set,
                ),
            ),
            ("Jobs", namespaced_list(batch.list_job_for_all_namespaces, batch.list_namespaced_job)),
            (
                "CronJobs",
                namespaced_list(
                    batch.list_cron_job_for_all_namespaces,
                    batch.list_namespaced_cron_job,
                ),
            ),
        )
    except (RuntimeError, ApiException) as exc:
        parser.exit(1, f"Unable to list Kubernetes resources: {exc}\n")

    print(f"Context: {context.name}    Scope: {namespace}")
    for heading, items in resource_lists:
        print(f"\n{heading}")
        if heading == "Pods":
            rows = [
                (
                    item.metadata.namespace or "-",
                    item.metadata.name or "-",
                    item.status.phase or "Unknown",
                    item.status.pod_ip or "-",
                    item.spec.node_name or "-",
                )
                for item in items
            ]
            print(
                render_table(
                    ("NAMESPACE", "NAME", "PHASE", "POD IP", "NODE"),
                    rows,
                )
            )
        else:
            print(render_table(("NAMESPACE", "NAME"), _namespace_rows(items)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
