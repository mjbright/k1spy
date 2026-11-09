#!/usr/bin/env python3
"""Patch one Kubernetes Node label; use --remove to delete a label key.

This is the only write example in the collection. It deliberately requires an
explicit --apply flag; without it, the proposed patch is printed only.
"""

from __future__ import annotations

import argparse
import json

from kubernetes import client
from kubernetes.client.exceptions import ApiException

from common.common import load_kubernetes_config


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("node", help="Node name.")
    parser.add_argument("label", help="Label key, optionally with a value as key=value.")
    parser.add_argument("--remove", action="store_true", help="Remove the label key.")
    parser.add_argument(
        "--apply", action="store_true", help="Send the patch to the Kubernetes API."
    )
    args = parser.parse_args()

    if args.remove:
        if "=" in args.label:
            parser.error("When using --remove, provide a key only (no '=value').")
        labels = {args.label: None}
    else:
        key, separator, value = args.label.partition("=")
        if not separator or not key or not value:
            parser.error("Provide a label in key=value form.")
        labels = {key: value}

    body = {"metadata": {"labels": labels}}
    print("Patch:")
    print(json.dumps(body, indent=2))
    if not args.apply:
        print("\nDry run only. Add --apply to modify the Node.")
        return 0

    try:
        context = load_kubernetes_config()
        node = client.CoreV1Api().patch_node(name=args.node, body=body)
    except (RuntimeError, ApiException) as exc:
        parser.exit(1, f"Unable to patch Node: {exc}\n")

    print(f"Updated Node {node.metadata.name!r} in context {context.name!r}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
