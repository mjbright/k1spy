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
        node_resources[node_name]={'req_cpu': 0.0, 'limit_cpu': 0.0, 'req_mem': 0.0, 'limit_mem': 0.0}
    if not namespace in ns_resources:
        ns_resources[namespace]={'req_cpu': 0.0, 'limit_cpu': 0.0, 'req_mem': 0.0, 'limit_mem': 0.0}

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
        if hasattr(resources.requests, 'cpu'):
            val=human_value_cpu(resources.requests.cpu)
            node_resources[node_name]['req_cpu']+=val
            ns_resources[namespace]['req_cpu']+=val
        if hasattr(resources.requests, 'memory'):
            val=human_value_memory(resources.requests.memory)
            node_resources[node_name]['req_mem']+=val
            ns_resources[namespace]['req_mem']+=val

        if resources.requests:
            ret_str+=f" REQ={resources.requests}"

    if hasattr(resources, 'limits'):
        if hasattr(resources.limits, 'cpu'):
            val=human_value_cpu(resources.limits.cpu)
            node_resources[node_name]['limit_cpu']+=val
            ns_resources[namespace]['limit_cpu']+=val
        if hasattr(resources.limits, 'memory'):
            val=human_value_memory(resources.limits.memory)
            node_resources[node_name]['limit_mem']+=val
            ns_resources[namespace]['limit_mem']+=val

        if resources.limits:
            ret_str+=f" LIMIT={resources.limits}"
    
    return ret_str

def human_value_memory(str_value):
    if str_value[-2:-1] == 'Ti':
        return float(str_value)*1000*1000*1000*1000
    if str_value[-2:-1] == 'Gi':
        return float(str_value)*1000*1000*1000
    if str_value[-2:-1] == 'Mi':
        return float(str_value)*1000*1000
    if str_value[-2:-1] == 'Ki':
        return float(str_value)*1000
    return float(str_value)

def human_value_cpu(str_value):
    if str_value[-1] == 'm':
        return float(str_value)/1000
    return float(str_value)


## -- Args: -------------------------------------------------------

namespace='default'

SHOW_RESOURCELESS_PODS=False

a=1
while a < len(sys.argv):
    arg=sys.argv[a]
    a+=1
    #print(f'**** {arg}')
    if arg == "-A":
        namespace=None
        continue

    if arg == "-n":
        namespace=sys.argv[a]
        a+=1
        continue

    if arg == "-a":
        SHOW_RESOURCELESS_PODS=True
        continue

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

    pod_resource_info=''
    for c in instance.spec.containers:
        if not hasattr(c, 'resources') and SHOW_RESOURCELESS_PODS:
            pod_resource_info+=f'- {c.name}\n'
        else:
            resource_str = get_resource_req_limits(c.resources, node_name, namespace, node_resources, ns_resources)
            if resource_str != '' or SHOW_RESOURCELESS_PODS:
                pod_resource_info+=f'- {c.name}: {resource_str}\n'
        #else:
            #print(f'NO {pod_name}')
    if pod_resource_info != '':
        sys.stdout.write(f'[{node_name}] {namespace}/{pod_name}\n{pod_resource_info}')

