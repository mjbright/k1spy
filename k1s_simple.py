#!/usr/bin/env python3

'''
    Very simple example of using Python Kubernetes bindings
'''

import os
import sys
from   kubernetes import client, config

## -- Get kubeconfig/cluster information: -------------------------

# Make sure ~/.kube/config is pointing to a valid cluster
HOME=os.getenv('HOME')
DEFAULT_KUBECONFIG=HOME+'/.kube/config'
KUBECONFIG=os.getenv('KUBECONFIG')

if KUBECONFIG is None:
    KUBECONFIG=DEFAULT_KUBECONFIG

#config.load_kube_config()
if os.path.exists(KUBECONFIG):
    print(f'Using KUBECONFIG={KUBECONFIG}')
    config.load_kube_config(KUBECONFIG)
else:
    print(f'No such kubeconfig file as "{KUBECONFIG}" - assuming in cluster')
    config.load_incluster_config()

## -- Get context/namespace  information: -------------------------

contexts, active_context = config.list_kube_config_contexts()
# {'context': {'cluster': 'kubernetes', 'namespace': 'k8scenario', 'user': 'kubernetes-admin'}, 'name': 'k8scenario'}
#print(active_context)
context=active_context['name']
print(f'context={context}')

## -- Get API clients: --------------------------------------------

corev1 = client.CoreV1Api()
#appsv1 = client.AppsV1Api()
#batchv1 = client.BatchV1Api()
#batchv1beta1 = client.BatchV1beta1Api()

## -- Access API: -------------------------------------------------

print("---- Nodes: -------------")
itemlist = corev1.list_node(watch=False)
for instance in itemlist.items:
    node_name = instance.metadata.name
    print(node_name)

p_namespace='default'
print(f"---- Pods: -------------- in '{p_namespace}' namespace")
#itemlist = corev1.list_pod_for_all_namespaces(watch=False)
itemlist = corev1.list_namespaced_pod(watch=False, namespace=p_namespace)
for instance in itemlist.items:
    pod_name = instance.metadata.name
    print(pod_name)

