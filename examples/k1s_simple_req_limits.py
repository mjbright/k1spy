#!/usr/bin/env python3

'''
    Very simple example of using Python Kubernetes bindings

    NOTE: See https://github.com/kubernetes-client/python/blob/master/kubernetes/README.md for API specs, e.g. search for CoreV1APi, then for methods ...
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
    ## -- Get context/namespace  information: -------------------------

    contexts, active_context = config.list_kube_config_contexts()
    # {'context': {'cluster': 'kubernetes', 'namespace': 'k8scenario', 'user': 'kubernetes-admin'}, 'name': 'k8scenario'}
    #print(active_context)
    context=active_context['name']
    print(f'context={context}')
else:
    print(f'No such kubeconfig file as "{KUBECONFIG}" - assuming in cluster')
    config.load_incluster_config()

## -- Func: -------------------------------------------------------

def die(msg):
    sys.stderr.write(f'{sys.argv[0]}: die - {msg}\n')
    sys.exit(1)

node_resources={}
ns_resources={}

def get_resource_req_limits(resources, node_name, namespace, node_resources, ns_resources):
    ret_str=''

    if not node_name in node_resources:
        node_resources[node_name]={'req': 0, 'limit': 0}
    if not namespace in ns_resources:
        ns_resources[namespace]={'req': 0, 'limit': 0}

    '''
    resources:
        limits:
            cpu: 800m
            memory: 1Gi
        requests:
            cpu: 400m
            memory: 700Mi
    '''
    if hasattr(resources, 'requests'):
        #ret_str+=f" REQ={resources['requests']}"
        ret_str+=f" REQ={resources.requests}"
    if hasattr(resources, 'limits'):
        #ret_str+=f" LIMIT={resources['limits']}"
        ret_str+=f" LIMIT={resources.limits}"
    
    return ret_str

## -- Args: -------------------------------------------------------

a=1

namespace='default'

SHOW_RESOURCELESS_PODS=False

while a < len(sys.argv):
    arg=sys.argv[a]
    a+=1
    if arg == "-A":
        namespace=None
        pass

    if arg == "-n":
        namespace=sys.argv[a]
        a+=1
        pass

    if arg == "-a":
        SHOW_RESOURCELESS_PODS=True
        pass

    die(f"Unknown option '{arg}'")

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

if namespace == None:
    print(f'---- Pods: --------------')
    itemlist = corev1.list_pod_for_all_namespaces(watch=False)
else:
    #p_namespace='default'
    print(f"---- Pods: -------------- in '{namespace}' namespace")
    itemlist = corev1.list_namespaced_pod(watch=False, namespace=namespace)

for instance in itemlist.items:
    node_name = instance.spec.node_name
    namespace = instance.metadata.namespace
    pod_name = instance.metadata.name

    sys.stdout.write(f'[{node_name}] {namespace}/{pod_name}\n')
    for c in instance.spec.containers:
        if not hasattr(c, 'resources') and SHOW_RESOURCELESS_PODS:
            print(f'- {c.name}')
        else:
            resource_str = get_resource_req_limits(c.resources, node_name, namespace, node_resources, ns_resources)
            print(f'- {c.name}: {resource_str}')
        #else:
            #print(f'NO {pod_name}')

