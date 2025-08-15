#!/usr/bin/env python3

'''
    Summarize request/limit settings across nodes/namespaces:

    USAGE:
       To see a summary of requests/limits for each Node, each Namespace
           ./k1s_simple_req_limits.py -a -A
       To see a Pod detail + summary of requests/limits for each Node, each Namespace
           ./k1s_simple_req_limits.py -a -A -d
       To see a Pod detail + summary of requests/limits for current Namespace
           ./k1s_simple_req_limits.py -a -A -d

    NOTE: See https://github.com/kubernetes-client/python/blob/master/kubernetes/README.md for API specs, e.g. search for CoreV1APi, then for methods ...
'''

import os
import sys
from   kubernetes import client, config

node_resources={}
ns_resources={}

namespace='default'

LIST_NODES_NAMESPACES=False
SHOW_RESOURCELESS_PODS=False
SHOW_DETAILS=False
VERBOSE=False

## -- Func: -------------------------------------------------------

def die(msg):
    sys.stderr.write(f'{sys.argv[0]}: die - {msg}\n')
    sys.exit(1)

def cumulate_resource_req_limits(resources, node_name, namespace):
    global node_resources, ns_resources

    ret_str=''

    '''
    resources:
        limits:
            cpu: 800m
            memory: 1Gi
        requests:
            cpu: 400m
            memory: 700Mi
    '''
    if hasattr(resources, 'requests') and resources.requests:
        if 'cpu' in resources.requests:
            val=from_human_value_cpu(resources.requests['cpu'])
            if VERBOSE: print(f'cpu==>{resources.requests["cpu"]} ==> {val}')
            node_resources[node_name]['req_cpu']+=val
            ns_resources[namespace]['req_cpu']+=val
        if 'memory' in resources.requests:
            val=from_human_value_memory(resources.requests['memory'])
            node_resources[node_name]['req_mem']+=val
            ns_resources[namespace]['req_mem']+=val

        if resources.requests:
            ret_str+=f" REQ={resources.requests}"

    if hasattr(resources, 'limits') and resources.limits:
        if 'cpu' in resources.limits:
            val=from_human_value_cpu(resources.limits['cpu'])
            node_resources[node_name]['limit_cpu']+=val
            ns_resources[namespace]['limit_cpu']+=val
        if 'memory' in resources.limits:
            val=from_human_value_memory(resources.limits['memory'])
            node_resources[node_name]['limit_mem']+=val
            ns_resources[namespace]['limit_mem']+=val

        if resources.limits:
            ret_str+=f" LIMIT={resources.limits}"
    
    return ret_str

def to_human_value_memory(value):
    if value > 1000*1000*1000*1000: return f'{value/1000/1000/1000/1000:8}Ti'
    if value > 1000*1000*1000:      return f'{value/1000/1000/1000:8}Gi'
    if value > 1000*1000:           return f'{value/1000/1000:8}Mi'
    if value > 1000:                return f'{value/1000:8}Ki'
    return f'{value:8}'

def from_human_value_memory(str_value):
    if str_value[-2:] == 'Ti': return float(str_value[:-2])*1000*1000*1000*1000
    if str_value[-2:] == 'Gi': return float(str_value[:-2])*1000*1000*1000
    if str_value[-2:] == 'Mi': return float(str_value[:-2])*1000*1000
    if str_value[-2:] == 'Ki': return float(str_value[:-2])*1000
    return float(str_value)

def from_human_value_cpu(str_value):
    if str_value[-1] == 'm':   return float(str_value[:-1])/1000
    return float(str_value)

def cumulate_items(itemlist):
    for instance in itemlist.items:
        node_name = instance.spec.node_name
        namespace = instance.metadata.namespace
        pod_name = instance.metadata.name

        pod_resource_info=''
        for c in instance.spec.containers:
            if not hasattr(c, 'resources') and SHOW_RESOURCELESS_PODS:
                pod_resource_info+=f'- {c.name}\n'
            else:
                resource_str = cumulate_resource_req_limits(c.resources, node_name, namespace)
                if resource_str != '' or SHOW_RESOURCELESS_PODS:
                    pod_resource_info+=f'- {c.name}: {resource_str}\n'

        if pod_resource_info != '' and SHOW_DETAILS:
            sys.stdout.write(f'[{node_name}] {namespace}/{pod_name}\n{pod_resource_info}')

def get_namespace_totals(namespace):
    req_cpu=ns_resources[namespace]['req_cpu']
    req_mem=ns_resources[namespace]['req_mem']
    limit_cpu=ns_resources[namespace]['limit_cpu']
    limit_mem=ns_resources[namespace]['limit_mem']
    return (req_cpu, req_mem, limit_cpu, limit_mem)

def get_node_totals(node):

    #print(node_resources[node])
    req_cpu=node_resources[node]['req_cpu']
    req_mem=node_resources[node]['req_mem']
    limit_cpu=node_resources[node]['limit_cpu']
    limit_mem=node_resources[node]['limit_mem']
    return (req_cpu, req_mem, limit_cpu, limit_mem)

## -- Args: -------------------------------------------------------

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

    if arg == "-l":
        LIST_NODES_NAMESPACES=True
        continue

    if arg == "-d":
        SHOW_DETAILS=True
        continue

    if arg == "-v":
        VERBOSE=True
        continue

    die(f"Unknown option '{arg}'")

## -- Get kubeconfig/cluster information: -------------------------

# Make sure ~/.kube/config is pointing to a valid cluster
HOME=os.getenv('HOME')
DEFAULT_KUBECONFIG=HOME+'/.kube/config'
KUBECONFIG=os.getenv('KUBECONFIG')

if KUBECONFIG is None:
    KUBECONFIG=DEFAULT_KUBECONFIG

#config.load_kube_config()
if os.path.exists(KUBECONFIG):
    if SHOW_DETAILS: print(f'Using KUBECONFIG={KUBECONFIG}')
    config.load_kube_config(KUBECONFIG)
    ## -- Get context/namespace  information: -------------------------

    contexts, active_context = config.list_kube_config_contexts()
    # {'context': {'cluster': 'kubernetes', 'namespace': 'k8scenario', 'user': 'kubernetes-admin'}, 'name': 'k8scenario'}
    #print(active_context)
    context=active_context['name']
    if SHOW_DETAILS: print(f'context={context}')
else:
    if SHOW_DETAILS: print(f'No such kubeconfig file as "{KUBECONFIG}" - assuming in cluster')
    config.load_incluster_config()

## -- Get API clients: --------------------------------------------

corev1 = client.CoreV1Api()
#appsv1 = client.AppsV1Api()

## -- Access API: -------------------------------------------------

if LIST_NODES_NAMESPACES: print("---- Nodes: -------------")
itemlist = corev1.list_node(watch=False)
nodes=[]
for instance in itemlist.items:
    node_name = instance.metadata.name
    nodes.append(node_name)
    node_resources[node_name]={'req_cpu': 0.0, 'limit_cpu': 0.0, 'req_mem': 0.0, 'limit_mem': 0.0}
    if LIST_NODES_NAMESPACES: print(node_name)

if LIST_NODES_NAMESPACES: print("---- Namespaces: --------")
itemlist = corev1.list_namespace(watch=False)
for instance in itemlist.items:
    loop_namespace = instance.metadata.name
    ns_resources[loop_namespace]={'req_cpu': 0.0, 'limit_cpu': 0.0, 'req_mem': 0.0, 'limit_mem': 0.0}
    if LIST_NODES_NAMESPACES: print(loop_namespace)

if namespace == None:
    print(f'---- Summary: --------------')
    #itemlist = corev1.list_pod_for_all_namespaces(watch=False)
    itemlist = corev1.list_namespace(watch=False)
    for item in itemlist.items:
        loop_namespace=item.metadata.name
        if VERBOSE: print(f'Listing Pods in {loop_namespace}:')
        itemlist = corev1.list_namespaced_pod(watch=False, namespace=loop_namespace)
        cumulate_items(itemlist)
        (req_cpu, req_mem, limit_cpu, limit_mem) = get_namespace_totals(loop_namespace)
        s_req_mem=to_human_value_memory(req_mem)
        s_limit_mem=to_human_value_memory(limit_mem)
        print(f'NAMESPACE {loop_namespace:15} total req_cpu={req_cpu:6.3} req_mem={s_req_mem} limit_cpu={limit_cpu:6.3} limit_mem={s_limit_mem}')
else:
    #p_namespace='default'
    print(f"---- Summary: -------------- in '{namespace}' namespace")
    itemlist = corev1.list_namespaced_pod(watch=False, namespace=namespace)
    cumulate_items(itemlist)
    (req_cpu, req_mem, limit_cpu, limit_mem) = get_namespace_totals(namespace)
    s_req_mem=to_human_value_memory(req_mem)
    s_limit_mem=to_human_value_memory(limit_mem)
    print(f'NAMESPACE {namespace:15} total req_cpu={req_cpu:6.3} req_mem={s_req_mem} limit_cpu={limit_cpu:6.3} limit_mem={s_limit_mem}')

for node in nodes:
    (req_cpu, req_mem, limit_cpu, limit_mem) = get_node_totals(node)
    s_req_mem=to_human_value_memory(req_mem)
    s_limit_mem=to_human_value_memory(limit_mem)
    print(f'NODE      {node:15} total req_cpu={req_cpu:6.3} req_mem={s_req_mem} limit_cpu={limit_cpu:6.3} limit_mem={s_limit_mem}')

