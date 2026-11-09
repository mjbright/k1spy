#!/usr/bin/env python3
"""Watch Deployment changes and display desired versus available replicas."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
import sys

from kubernetes import client, watch
from kubernetes.client.exceptions import ApiException

from common.common import load_kubernetes_config


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    scope = parser.add_mutually_exclusive_group()
    scope.add_argument("-A", "--all-namespaces", action="store_true")
    scope.add_argument("-n", "--namespace", help="Namespace to watch.")
    parser.add_argument("--label-selector", help="Kubernetes label selector.")
    args = parser.parse_args()

    try:
        context = load_kubernetes_config()
        apps = client.AppsV1Api()
        stream = watch.Watch()
        namespace = "all namespaces" if args.all_namespaces else args.namespace or context.namespace
        print(f"Watching Deployments in {namespace} (context: {context.name}).", flush=True)

        while True:
            try:
                options = {"label_selector": args.label_selector, "timeout_seconds": 30}
                events = (
                    stream.stream(apps.list_deployment_for_all_namespaces, **options)
                    if args.all_namespaces
                    else stream.stream(
                        apps.list_namespaced_deployment,
                        namespace=args.namespace or context.namespace,
                        **options,
                    )
                )
                for event in events:
                    deployment = event["object"]
                    spec = deployment.spec
                    status = deployment.status
                    record = {
                        "time": datetime.now(UTC).isoformat(timespec="seconds"),
                        "event": event["type"],
                        "namespace": deployment.metadata.namespace,
                        "name": deployment.metadata.name,
                        "replicas": {
                            "desired": spec.replicas or 0,
                            "ready": status.ready_replicas or 0,
                            "available": status.available_replicas or 0,
                        },
                        "resource_version": deployment.metadata.resource_version,
                    }
                    print(json.dumps(record, separators=(",", ":")), flush=True)
            except ApiException as exc:
                if exc.status == 410:
                    print(
                        "Watch resource version expired; restarting the watch.",
                        file=sys.stderr,
                        flush=True,
                    )
                    stream.stop()
                    stream = watch.Watch()
                    continue
                raise
    except KeyboardInterrupt:
        print("\nWatch stopped.", file=sys.stderr)
    except (RuntimeError, ApiException) as exc:
        parser.exit(1, f"Unable to watch Deployments: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
