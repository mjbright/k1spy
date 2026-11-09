#!/usr/bin/env python3
"""Create a namespaced Job using the Kubernetes Python client.

The creation payload is harmless until --apply is provided. The API-generated
Job is normally short-lived; use --ttl-seconds-after-finished to let Kubernetes
garbage-collect it after completion.
"""

from __future__ import annotations

import argparse
import json

from kubernetes import client
from kubernetes.client.exceptions import ApiException

from common.common import load_kubernetes_config


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("name", help="Job name.")
    parser.add_argument("--namespace", help="Target namespace (defaults to context namespace).")
    parser.add_argument("--image", default="busybox:1.36", help="Container image.")
    parser.add_argument(
        "--command",
        action="append",
        default=None,
        help="Container command/argument (repeat as needed). Default: sh -c 'echo hello; sleep 5'.",
    )
    parser.add_argument("--apply", action="store_true", help="Create the Job.")
    parser.add_argument(
        "--ttl-seconds-after-finished",
        type=int,
        default=300,
        help="TTL cleanup seconds after completion; default 300.",
    )
    args = parser.parse_args()
    if args.ttl_seconds_after_finished < 0:
        parser.error("--ttl-seconds-after-finished cannot be negative.")

    command = args.command or ["sh", "-c", "echo hello from Kubernetes; sleep 5"]
    manifest = client.V1Job(
        metadata=client.V1ObjectMeta(name=args.name),
        spec=client.V1JobSpec(
            backoff_limit=0,
            ttl_seconds_after_finished=args.ttl_seconds_after_finished,
            template=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(labels={"job-name": args.name}),
                spec=client.V1PodSpec(
                    restart_policy="Never",
                    containers=[
                        client.V1Container(
                            name="task",
                            image=args.image,
                            command=command,
                        )
                    ],
                ),
            ),
        ),
    )
    print("Job manifest:")
    print(json.dumps(client.ApiClient().sanitize_for_serialization(manifest), indent=2))
    if not args.apply:
        print("\nDry run only. Add --apply to create the Job.")
        return 0

    try:
        context = load_kubernetes_config()
        namespace = args.namespace or context.namespace
        created = client.BatchV1Api().create_namespaced_job(
            namespace=namespace,
            body=manifest,
        )
    except (RuntimeError, ApiException) as exc:
        parser.exit(1, f"Unable to create Job: {exc}\n")

    print(f"Created Job {created.metadata.name!r} in namespace {namespace!r}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
