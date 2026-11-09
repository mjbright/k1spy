#!/usr/bin/env python3
"""Watch Pod ADDED, MODIFIED and DELETED notifications."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
import sys
import time

from kubernetes import client, watch
from kubernetes.client.exceptions import ApiException

from common.common import load_kubernetes_config


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    scope = parser.add_mutually_exclusive_group()
    scope.add_argument("-A", "--all-namespaces", action="store_true")
    scope.add_argument("-n", "--namespace", help="Namespace to watch.")
    parser.add_argument(
        "--label-selector", help="Only watch Pods matching this Kubernetes label selector."
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=0,
        help="Stop watching after this many seconds (0 means continue until interrupted).",
    )
    args = parser.parse_args()
    if args.timeout < 0:
        parser.error("--timeout cannot be negative.")

    try:
        context = load_kubernetes_config()
        core = client.CoreV1Api()
        stream = watch.Watch()
        print(
            f"Watching Pods in {'all namespaces' if args.all_namespaces else args.namespace or context.namespace!r}"
            f" (context: {context.name}); press Ctrl-C to stop.",
            flush=True,
        )
        deadline = time.monotonic() + args.timeout if args.timeout else None

        def events():
            remaining = (
                max(1, min(30, int(deadline - time.monotonic())))
                if deadline is not None
                else 30
            )
            options = {
                "label_selector": args.label_selector,
                "timeout_seconds": remaining,
            }
            if args.all_namespaces:
                yield from stream.stream(core.list_pod_for_all_namespaces, **options)
            else:
                yield from stream.stream(
                    core.list_namespaced_pod,
                    namespace=args.namespace or context.namespace,
                    **options,
                )

        while deadline is None or time.monotonic() < deadline:
            try:
                for event in events():
                    pod = event["object"]
                    metadata = pod.metadata
                    status = pod.status
                    record = {
                        "time": datetime.now(UTC).isoformat(timespec="seconds"),
                        "event": event["type"],
                        "namespace": metadata.namespace,
                        "name": metadata.name,
                        "phase": status.phase if status else None,
                        "pod_ip": status.pod_ip if status else None,
                        "resource_version": metadata.resource_version,
                    }
                    print(json.dumps(record, separators=(",", ":")), flush=True)
                    if deadline is not None and time.monotonic() >= deadline:
                        break
                # A finite Kubernetes watch stream closes periodically. Starting
                # a new stream resumes from the latest state automatically.
            except ApiException as exc:
                if exc.status == 410:
                    print(
                        "Watch resource version expired; relisting and resuming.",
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
        parser.exit(1, f"Unable to watch Pods: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
