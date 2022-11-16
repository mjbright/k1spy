#!/usr/bin/env python
# coding: utf-8

# In[1]:


get_ipython().system('kubectl get nodes --show-labels')


# In[44]:


from pprint import pprint
from kubernetes import client, config

def set_node_labels(node_name='minikube'):
    config.load_kube_config()

    api_instance = client.CoreV1Api()

    body = {
        "metadata": {
            "labels": {
                "label1": "value1", # OK
                "label2": "value2", # OK
                "emptylabel": None  # Not working
            }
        }
    }

    api_response = api_instance.patch_node(node_name, body)

    pprint(api_response)
    
set_node_labels('master')


# In[7]:


get_ipython().system('kubectl get nodes --show-labels')


# In[81]:


def main():
    #config.load_incluster_config()
    config.load_kube_config()

    corev1 = client.CoreV1Api()
    print("Listing pods with their IPs:")
    ret = corev1.list_pod_for_all_namespaces(watch=False)
    for i in ret.items:
        print(f"{i.metadata.namespace:12s} {i.metadata.name:42s} {i.status.pod_ip:16s} {i.status.host_ip:16s}")
        #print("%-12s  %-42s %16s %16s" % (i.metadata.namespace, i.metadata.name, i.status.pod_ip, i.status.host_ip))

main()


# In[82]:


config.load_kube_config()
#config.load_incluster_config()
#v1 = None
corev1 = client.CoreV1Api()
appsv1 = client.AppsV1Api()
batchv1 = client.BatchV1Api()
#batchv1beta1 = client.BatchV1beta1Api()


# In[83]:


dir(client)


# In[84]:


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
        
#print("Listing nodes with their IPs:")
nodes = get_nodes()


# In[85]:


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

print("[all namespaces] Listing pods with their IPs:")
get_pods()

print()
print("[namespace='default'] Listing pods with their IPs:")
get_pods(namespace='default')


# In[86]:


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
        
print("[all namespaces] Listing deployments:")
get_deployments()

print()
print("[namespace='default'] Listing deployments:")
get_deployments(namespace='default')


# In[87]:


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
        
print("[all namespaces] Listing daemonsets:")
get_daemon_sets()

print()
print("[namespace='default'] Listing daemonsets:")
get_daemon_sets(namespace='default')


# In[88]:


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
        
print("[all namespaces] Listing replicasets:")
get_replica_sets()

print()
print("[namespace='default'] Listing replicasets:")
get_replica_sets(namespace='default')


# In[90]:


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
        
print("[all namespaces] Listing services:")
get_services()

print()
print("[namespace='default'] Listing services:")
get_services(namespace='default')


# In[91]:


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
        
print("[all namespaces] Listing jobs:")
get_jobs()

print()
print("[namespace='default'] Listing jobs:")
get_jobs(namespace='default')


# In[92]:


def get_cronjobs(namespace='all'):
    if namespace == 'all':
        ret = batchv1.list_cron_job_for_all_namespaces(watch=False)
    else:
        ret = batchv1.list_namespaced_cron_job(watch=False, namespace=namespace)
    for i in ret.items:
        #deploy_name = i.metadata.name
        #deploy_namespace = i.metadata.namespace
        #print("%-12s  %-42s" % (deploy_namespace, deploy_name))
        print(f"{i.metadata.namespace:12s} {i.metadata.name:42s}")
        
print("[all namespaces] Listing cronjobs:")
get_cronjobs()

print()
print("[namespace='default'] Listing cronjobs:")
get_cronjobs(namespace='default')


# In[43]:


methods = [ method for method in dir(v1) if "reso" in method]
print("\n".join( methods ))


# In[ ]:




