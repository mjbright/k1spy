#!/usr/bin/env python3

# Remember to make sure ~/.kube/config is pointing to a valid cluster or kubernetes import will timeout ... after quite a while ...

#import datetime;
#now = datetime.datetime.now(); print(now)
#from pprint import pprint

from kubernetes import client, config
#now = datetime.datetime.now(); print(now)

config.load_kube_config()
#config.load_incluster_config()

# Get API clients:
corev1 = client.CoreV1Api()
appsv1 = client.AppsV1Api()
batchv1 = client.BatchV1Api()
batchv1beta1 = client.BatchV1beta1Api()

# To see available APIs:
#print( dir(client) )
# Search for methods on APIs:
#    match="list_pod"
#    methods = [ method for method in dir(v1) if match in method]
#    print("\n".join( methods ))

def get_nodes():
    nodes = {}

    ret = corev1.list_node(watch=False)
    for i in ret.items:
        node_ip   = i.status.addresses[0].address
        node_name = i.metadata.name
        #print("%-12s  %-16s" % (node_name, node_ip))
        print(f"{i.metadata.name:12s} {node_ip:16s}")
        nodes[node_ip] = node_name
    return nodes
        
def get_pods(namespace='all'):
    if namespace == 'all':
        ret = corev1.list_pod_for_all_namespaces(watch=False)
    else:
        ret = corev1.list_namespaced_pod(watch=False, namespace=namespace)
    for i in ret.items:
        pod_name = i.metadata.name
        pod_namespace = i.metadata.namespace
        pod_ip = i.status.pod_ip
        host_ip = i.status.host_ip
        host = host_ip
        if host_ip in nodes:
            host = nodes[host_ip]
        print(f"{i.metadata.namespace:12s} {i.metadata.name:42s} {i.status.pod_ip:16s} {i.status.host_ip:16s}")
        #print("%-12s  %-42s %16s %16s" % (pod_namespace, pod_name, pod_ip, host))

def get_deployments(namespace='all'):
    if namespace == 'all':
        ret = appsv1.list_deployment_for_all_namespaces(watch=False)
    else:
        ret = appsv1.list_namespaced_deployment(watch=False, namespace=namespace)
    for i in ret.items:
        #deploy_name = i.metadata.name
        #deploy_namespace = i.metadata.namespace
        #print("%-12s  %-42s" % (deploy_namespace, deploy_name))
        print(f"{i.metadata.namespace:12s} {i.metadata.name:42s}")
        

def get_daemon_sets(namespace='all'):
    if namespace == 'all':
        ret = appsv1.list_daemon_set_for_all_namespaces(watch=False)
    else:
        ret = appsv1.list_namespaced_daemon_set(watch=False, namespace=namespace)
    for i in ret.items:
        #deploy_name = i.metadata.name
        #deploy_namespace = i.metadata.namespace
        #print("%-12s  %-42s" % (deploy_namespace, deploy_name))
        print(f"{i.metadata.namespace:12s} {i.metadata.name:42s}")
        

def get_replica_sets(namespace='all'):
    if namespace == 'all':
        ret = appsv1.list_replica_set_for_all_namespaces(watch=False)
    else:
        ret = appsv1.list_namespaced_replica_set(watch=False, namespace=namespace)
    for i in ret.items:
        #deploy_name = i.metadata.name
        #deploy_namespace = i.metadata.namespace
        #print("%-12s  %-42s" % (deploy_namespace, deploy_name))
        print(f"{i.metadata.namespace:12s} {i.metadata.name:42s}")
        

def get_services(namespace='all'):
    if namespace == 'all':
        ret = corev1.list_service_for_all_namespaces(watch=False)
    else:
        ret = corev1.list_namespaced_service(watch=False, namespace=namespace)
    for i in ret.items:
        #deploy_name = i.metadata.name
        #deploy_namespace = i.metadata.namespace
        #print("%-12s  %-42s" % (deploy_namespace, deploy_name))
        print(f"{i.metadata.namespace:12s} {i.metadata.name:42s}")
        

def get_jobs(namespace='all'):
    if namespace == 'all':
        ret = batchv1.list_job_for_all_namespaces(watch=False)
    else:
        ret = batchv1.list_namespaced_job(watch=False, namespace=namespace)
    for i in ret.items:
        #deploy_name = i.metadata.name
        #deploy_namespace = i.metadata.namespace
        #print("%-12s  %-42s" % (deploy_namespace, deploy_name))
        print(f"{i.metadata.namespace:12s} {i.metadata.name:42s}")
        

def get_cronjobs(namespace='all'):
    if namespace == 'all':
        ret = batchv1beta1.list_cron_job_for_all_namespaces(watch=False)
    else:
        ret = batchv1beta1.list_namespaced_cron_job(watch=False, namespace=namespace)
    for i in ret.items:
        #deploy_name = i.metadata.name
        #deploy_namespace = i.metadata.namespace
        #print("%-12s  %-42s" % (deploy_namespace, deploy_name))
        print(f"{i.metadata.namespace:12s} {i.metadata.name:42s}")
        
def test_methods():
    print("\n======== Listing nodes with their IPs:")
    nodes = get_nodes()
    
    print("\n======== [all namespaces] Listing pods with their IPs:")
    get_pods()
    print("\n---- [namespace='default'] Listing pods with their IPs:")
    get_pods(namespace='default')
    
    print("\n======== [all namespaces] Listing deployments:")
    get_deployments()
    print("\n---- [namespace='default'] Listing deployments:")
    get_deployments(namespace='default')
    
    print("\n======== [all namespaces] Listing daemonsets:")
    get_daemon_sets()
    print("\n---- [namespace='default'] Listing daemonsets:")
    get_daemon_sets(namespace='default')
    
    print("\n======== [all namespaces] Listing replicasets:")
    get_replica_sets()
    print("\n---- [namespace='default'] Listing replicasets:")
    get_replica_sets(namespace='default')
    
    print("\n======== [all namespaces] Listing services:")
    get_services()
    print("\n---- [namespace='default'] Listing services:")
    get_services(namespace='default')
    
    print("\n======== [all namespaces] Listing jobs:")
    get_jobs()
    print("\n---- [namespace='default'] Listing jobs:")
    get_jobs(namespace='default')
    
    print("\n======== [all namespaces] Listing cronjobs:")
    get_cronjobs()
    print("\n---- [namespace='default'] Listing cronjobs:")
    get_cronjobs(namespace='default')

test_methods()


