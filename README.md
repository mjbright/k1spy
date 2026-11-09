# Kubernetes Python client examples

This package contains reviewed Python 3.12+ examples built around the official
`kubernetes` Python client. The original uploaded files are preserved; these
scripts are a cleaned-up, separate collection.

## Files and examples

| Script | Demonstrates |
| --- | --- |
| `k1s.py` | Compact Pod-first overview, optional extended details, refresh loop, UTC-safe age display |
| `my_client_examples.py` | Combined read-only Pod, Service, Deployment, DaemonSet, ReplicaSet, Job, and CronJob listing |
| `list_pods.py` | List Pods in a namespace or across namespaces |
| `simple_client.py` | Minimal node and namespace-scoped Pod queries |
| `kubernetes-python_simple_req_limits.py` | Resource request/limit totals by namespace and node |
| `patch_node_labels.py` | Node label patch and label removal (dry-run by default) |
| `create_job.py` | Construct and optionally create a namespaced Job (dry-run by default) |
| `watch_pods.py` | Pod ADDED/MODIFIED/DELETED notifications as JSON Lines |
| `watch_deployments.py` | Deployment notifications with desired/ready/available replica counts |
| `test_examples.py` | Offline unit tests for age, column alignment, and resource quantity parsing |

The small `kube_examples` package holds shared kubeconfig and table-formatting
helpers. The dependency is also listed in `requirements.txt`.

## Requirements

- Python 3.12 or newer (the source syntax uses modern standard-library typing)
- Kubernetes Python client 32.x, compatible with Kubernetes 1.32+
- A kubeconfig or a Pod ServiceAccount with appropriate RBAC

Install the Kubernetes client:

```console
python -m pip install -r requirements.txt
```

When installing the folder as a Python project, its `pyproject.toml` declares
Python 3.12+ and the same Kubernetes client dependency.

Run scripts from this directory so Python can import the `kube_examples`
package. To use a specific configuration file, set `KUBECONFIG`; otherwise
normal kubeconfig resolution applies. In-cluster credentials are selected when
`KUBERNETES_SERVICE_HOST` is present.

## Examples

```console
python list_pods.py
python list_pods.py --namespace kube-system
python my_client_examples.py --all-namespaces
python k1s.py --all-namespaces --resource pods --resource services --once
python k1s.py --namespace default --interval 2
python k1s.py --resource all --details --interval 2
python k1s.py --color always
python kubernetes-python_simple_req_limits.py --all-namespaces --details
python watch_pods.py --namespace default --label-selector app=demo
python watch_deployments.py --all-namespaces
python -m unittest -v
```

Watches stream Kubernetes API events until interrupted with Ctrl-C. RBAC must
permit `list` and `watch` on the corresponding resource types. Kubernetes
periodically closes finite watches; the examples reconnect. HTTP 410
`ResourceExpired` errors are handled by restarting from current list state (the
API may not replay notifications older than the retained resource version).

## Safety and scope

All listing and watch examples are read-only. `patch_node_labels.py` and
`create_job.py` print the proposed request and perform no mutation unless
`--apply` is supplied. Review the generated payload, selected context, target,
namespace, and permissions before applying. A label value of `key=value` is
set; `--remove key` uses JSON merge-patch null to delete a key.

The request/limit example sums the requests and limits for regular application
containers. It intentionally does not model init-container scheduling maxima,
Pod overhead, admission defaults, or cluster capacity; treat it as an
educational report rather than a scheduler-equivalent capacity calculator.

## Review notes on the supplied files

- `my_client_examples.py` was a notebook export with `get_ipython()` calls,
  live API calls at import time, repeated blocks, and brittle node-address
  assumptions. The refreshed files use ordinary entry points, helpers, and
  explicit missing-value handling.
- The uploaded `kubernetes-python_list_pods.py` treated a truthy return from
  `load_kube_config()` as a reason to load in-cluster credentials. Those
  credential paths are now selected explicitly.
- `k1s.py` formatted fields before coloring but later applied field widths to
  strings that include ANSI escape codes, and some per-resource layouts had
  unrelated fixed widths. The new implementation calculates each column width
  from its actual content, including long image and IP values. By default it
  shows only Pods and the concise namespace/type/name/ready/status/age columns;
  choose resource types explicitly (or `all`) and add `--details` to show IPs,
  images, ports, and other extended fields for a demo. Compact tables preserve
  the original semantic color cues on READY/STATUS: green for healthy, yellow
  for pending/partial, and red for failed or zero-ready. Color is automatic in
  terminals; `--color always|never` overrides it, and `NO_COLOR` is respected.
- Its age formatter used `datetime.strptime()` and `time.mktime()` (which
  applies local timezone rules to a UTC Kubernetes timestamp) and then
  `strip('0')` (which removes any leading zero, not only the first duration
  component). The replacement uses timezone-aware UTC arithmetic and `divmod`;
  a resource 3 minutes and 5 seconds old renders as `3m05s`.
- The old request/limit script used mutable global dictionaries, assumed every
  Pod was scheduled, handled only a subset of Kubernetes quantity suffixes,
  and could fail on empty namespaces or nodes. The rewrite uses decimal
  quantities, explicit scope, and zero-filled totals. Its stated simplification
  is documented above.
