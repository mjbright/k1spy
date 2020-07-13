#!/usr/bin/env python3

SHOW_TYPES=True

# Remember to make sure ~/.kube/config is pointing to a valid cluster or kubernetes import will timeout ... after quite a while ...

        
#import datetime;
#now = datetime.datetime.now(); print(now)
#from pprint import pprint

import sys, time
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

#============ COLOUR DEFINITIONS ==============================

BLACK = '\033[30m'
RED = '\033[31m'
GREEN = '\033[32m'
YELLOW = '\033[33m'
BLUE = '\033[34m'
MAGENTA = '\033[35m'
CYAN = '\033[36m'
WHITE = '\033[37m'
UNDERLINE = '\033[4m'
RESET = '\033[0m'

BOLD_BLACK = '\033[30;1m'
BOLD_RED = '\033[31;1m'
BOLD_GREEN = '\033[32;1m'
BOLD_YELLOW = '\033[33;1m'
BOLD_BLUE = '\033[34;1m'
BOLD_MAGENTA = '\033[35;1m'
BOLD_CYAN = '\033[36;1m'
BOLD_WHITE = '\033[37;1m'

def black(msg):    return f"{BLACK}{msg}{RESET}"
def red(msg):      return f"{RED}{msg}{RESET}"
def green(msg):    return f"{GREEN}{msg}{RESET}"
def yellow(msg):   return f"{YELLOW}{msg}{RESET}"
def blue(msg):     return f"{BLUE}{msg}{RESET}"
def magenta(msg):  return f"{MAGENTA}{msg}{RESET}"
def cyan(msg):     return f"{CYAN}{msg}{RESET}"
def white(msg):    return f"{WHITE}{msg}{RESET}"
def underline(msg): return f"{UNDERLINE}{msg}{RESET}"
def reset(msg):    return f"{RESET}{msg}{RESET}"

def bold_black(msg):    return f"{BOLD_BLACK}{msg}{RESET}"
def bold_red(msg):      return f"{BOLD_RED}{msg}{RESET}"
def bold_green(msg):    return f"{BOLD_GREEN}{msg}{RESET}"
def bold_yellow(msg):   return f"{BOLD_YELLOW}{msg}{RESET}"
def bold_blue(msg):     return f"{BOLD_BLUE}{msg}{RESET}"
def bold_magenta(msg):  return f"{BOLD_MAGENTA}{msg}{RESET}"
def bold_cyan(msg):     return f"{BOLD_CYAN}{msg}{RESET}"
def bold_white(msg):    return f"{BOLD_WHITE}{msg}{RESET}"

#print(red("Hello"),"there",blue("how"),"are you?")
#print(underline("Hello"),"there",green("how"),yellow("are you?"))

#= END OF === COLOUR DEFINITIONS ==============================


def sprint_nodes():
    #global nodes
    #nodes = {}

    type =  'node/' if SHOW_TYPES else ''

    ret = corev1.list_node(watch=False)
    retstr = ""
    for i in ret.items:
        node_ip   = i.status.addresses[0].address
        node_name = i.metadata.name
        retstr += f"{type}{i.metadata.name:12s} { green( node_ip ) :16s}\n"
        #info=$(c 32)$(jq -r '.object.status.addresses[0].address' <<<"$event")$(c 0);;
        #nodes[node_ip] = node_name
    return retstr

def print_nodes(): print(sprint_nodes())

def get_nodes():
    nodes = {}

    ret = corev1.list_node(watch=False)
    for i in ret.items:
        node_ip   = i.status.addresses[0].address
        node_name = i.metadata.name
        nodes[node_ip] = node_name
    return nodes
        
def print_pods(namespace='all'): print(sprint_pods(namespace))

def sprint_pods(namespace='all'):
    op=''
    type =  'pod/' if SHOW_TYPES else ''

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
            if   "ma" in host: host=cyan(host)
            elif "wo" in host: host=magenta(host)
            else:              pass
        #print(f"{i.metadata.namespace:12s} {i.metadata.name:42s} {i.status.pod_ip:16s} {i.status.host_ip:16s}")
        phase=i.status.phase
        is_ready=False
        is_scheduled=False
        for cond in i.status.conditions:
            if cond.type == 'Ready'        and cond.status == "True": is_ready=True
            if cond.type == 'PodScheduled' and cond.status == "True": is_scheduled=True
        #print(i.status.conditions)
        if is_scheduled and (not is_ready):
            info='NonReady'
        else:
            info=phase
        if info == "Running": info=green("Running")
        op += f"{type}{i.metadata.namespace:12s} {i.metadata.name:42s} {i.status.pod_ip:16s} {host:16s} {info}\n"
    return op

def print_deployments(namespace='all'): print(sprint_deployments(namespace))

def sprint_deployments(namespace='all'):
    op=''
    type =  'deploy/' if SHOW_TYPES else ''

    if namespace == 'all':
        ret = appsv1.list_deployment_for_all_namespaces(watch=False)
    else:
        ret = appsv1.list_namespaced_deployment(watch=False, namespace=namespace)
    for i in ret.items:
        #print(f"{i.metadata.namespace:12s} {i.metadata.name:42s}")
        spec=i.spec.replicas
        stat=i.status.ready_replicas
        if stat == spec:
            info=green(f'{stat}/{spec}')
        else:
            info=yellow(f'{stat}/{spec}')
        op += f"{type}{i.metadata.namespace:12s} {i.metadata.name:42s} {info}\n"
        #op += f"{type}{i.metadata.namespace:12s} {i.metadata.name:42s}\n"
    return op
        

def print_daemon_sets(namespace='all'): print(sprint_daemon_sets(namespace))

def sprint_daemon_sets(namespace='all'):
    op=''
    type =  'ds/' if SHOW_TYPES else ''

    if namespace == 'all':
        ret = appsv1.list_daemon_set_for_all_namespaces(watch=False)
    else:
        ret = appsv1.list_namespaced_daemon_set(watch=False, namespace=namespace)
    for i in ret.items:
        #print(f"{i.metadata.namespace:12s} {i.metadata.name:42s}")
        op += f"{type}{i.metadata.namespace:12s} {i.metadata.name:42s}\n"
    return op
        
def print_stateful_sets(namespace='all'): print(sprint_stateful_sets(namespace))

def sprint_stateful_sets(namespace='all'):
    op=''
    type =  'ss/' if SHOW_TYPES else ''

    if namespace == 'all':
        ret = appsv1.list_stateful_set_for_all_namespaces(watch=False)
    else:
        ret = appsv1.list_namespaced_stateful_set(watch=False, namespace=namespace)
    for i in ret.items:
        #print(f"{i.metadata.namespace:12s} {i.metadata.name:42s}")
        spec=i.spec.replicas
        stat=i.status.ready_replicas
        if stat == spec:
            info=green(f'{stat}/{spec}')
        else:
            info=yellow(f'{stat}/{spec}')
        op += f"{type}{i.metadata.namespace:12s} {i.metadata.name:42s} {info}\n"
        #op += f"{type}{i.metadata.namespace:12s} {i.metadata.name:42s}\n"
    return op
        

def print_replica_sets(namespace='all'): print(sprint_replica_sets(namespace))

def sprint_replica_sets(namespace='all'):
    op=''
    type =  'rs/' if SHOW_TYPES else ''

    if namespace == 'all':
        ret = appsv1.list_replica_set_for_all_namespaces(watch=False)
    else:
        ret = appsv1.list_namespaced_replica_set(watch=False, namespace=namespace)
    for i in ret.items:
        #print(f"{i.metadata.namespace:12s} {i.metadata.name:42s}")
        #stat=0 #print(i.status) #sys.exit(0) #if 'readyReplicas' in i.status: stat=i.status.readyReplicas
        spec=i.spec.replicas
        stat=i.status.ready_replicas
        if stat == spec:
            info=green(f'{stat}/{spec}')
        else:
            info=yellow(f'{stat}/{spec}')
        op += f"{type}{i.metadata.namespace:12s} {i.metadata.name:42s} {info}\n"
    return op
        

def print_services(namespace='all'): print(sprint_services(namespace))

def sprint_services(namespace='all'):
    op=''
    type =  'svc/' if SHOW_TYPES else ''

    if namespace == 'all':
        ret = corev1.list_service_for_all_namespaces(watch=False)
    else:
        ret = corev1.list_namespaced_service(watch=False, namespace=namespace)
    for i in ret.items:
        #print(f"{i.metadata.namespace:12s} {i.metadata.name:42s}")
        op += f"{type}{i.metadata.namespace:12s} {i.metadata.name:42s}\n"
    return op
        

def print_jobs(namespace='all'): print(sprint_jobs(namespace))

def sprint_jobs(namespace='all'):
    op=''
    type =  'job/' if SHOW_TYPES else ''

    if namespace == 'all':
        ret = batchv1.list_job_for_all_namespaces(watch=False)
    else:
        ret = batchv1.list_namespaced_job(watch=False, namespace=namespace)
    for i in ret.items:
        #print(f"{i.metadata.namespace:12s} {i.metadata.name:42s}")
        op += f"{type}{i.metadata.namespace:12s} {i.metadata.name:42s}\n"
    return op


def print_cron_jobs(namespace='all'): print(sprint_cron_jobs(namespace))

def sprint_cron_jobs(namespace='all'):
    op=''
    type =  'cronjob/' if SHOW_TYPES else ''

    if namespace == 'all':
        ret = batchv1beta1.list_cron_job_for_all_namespaces(watch=False)
    else:
        ret = batchv1beta1.list_namespaced_cron_job(watch=False, namespace=namespace)
    for i in ret.items:
        #print(f"{i.metadata.namespace:12s} {i.metadata.name:42s}")
        op += f"{type}{i.metadata.namespace:12s} {i.metadata.name:42s}\n"
    return op
        
def test_methods():
    global nodes
    nodes = get_nodes()

    print("\n======== Listing nodes with their IPs:")
    print_nodes()
    
    print("\n======== [all namespaces] Listing pods with their IPs:")
    print_pods()
    print("\n---- [namespace='default'] Listing pods with their IPs:")
    print_pods(namespace='default')
    
    print("\n======== [all namespaces] Listing deployments:")
    print_deployments()
    print("\n---- [namespace='default'] Listing deployments:")
    print_deployments(namespace='default')
    
    print("\n======== [all namespaces] Listing daemon_sets:")
    print_daemon_sets()
    print("\n---- [namespace='default'] Listing daemon_sets:")
    print_daemon_sets(namespace='default')
    
    print("\n======== [all namespaces] Listing stateful_sets:")
    print_stateful_sets()
    print("\n---- [namespace='default'] Listing stateful_sets:")
    print_stateful_sets(namespace='default')
    
    print("\n======== [all namespaces] Listing replica_sets:")
    print_replica_sets()
    print("\n---- [namespace='default'] Listing replica_sets:")
    print_replica_sets(namespace='default')
    
    print("\n======== [all namespaces] Listing services:")
    print_services()
    print("\n---- [namespace='default'] Listing services:")
    print_services(namespace='default')
    
    print("\n======== [all namespaces] Listing jobs:")
    print_jobs()
    print("\n---- [namespace='default'] Listing jobs:")
    print_jobs(namespace='default')
    
    print("\n======== [all namespaces] Listing cron_jobs:")
    print_cron_jobs()
    print("\n---- [namespace='default'] Listing cron_jobs:")
    print_cron_jobs(namespace='default')

#test_methods()

default_namespace="default"
default_resources=["pods"]

# Clears but keeps at bottom of screeen:
#def cls(): print(chr(27) + "[2J")
# Clears and positions at top of screeen:
def cls(): print('\033[H\033[J')

a=1

namespace=None
resources=[]

while a <= (len(sys.argv)-1):
    arg=sys.argv[a];
    #print(f'sys.argv[{a}]={sys.argv[a]}')
    a+=1
    if arg == "-st":            SHOW_TYPES=True;  continue
    if arg == "-show-types":    SHOW_TYPES=True;  continue
    if arg == "-nst":           SHOW_TYPES=False; continue
    if arg == "-no-show-types": SHOW_TYPES=False; continue

    if arg == "-test":
        test_methods()
        sys.exit(0)

    if arg == "-slow":
        # Slow changing resources:
        resources = [ 'node', 'svc', 'deploy', 'ds', 'rs', 'ss' ]
        continue

    if arg == "-n":
        namespace=sys.argv[a];
        a+=1;
        continue
    if arg == "-r":
        resources.append(sys.argv[a]);
        a+=1;
        continue

    if namespace == None: namespace = arg; continue
    #if resources == []: resources = [arg]; continue
    resources.append( arg )
    #die
    #print(arg)

final_resources=[]
for reslist in resources:
    #print(f'reslist={reslist}')
    res = reslist.split(",")
    final_resources.extend(res)
    #print(f'final_resources={final_resources}')

resources=final_resources

if namespace == None: namespace=default_namespace
if namespace == "-": namespace="all"

if len(resources) == 0: resources = [default_resources]

print(f'namespace={namespace}')
print(f'resources={resources}')
#sys.exit(0)

last_op=''
while True:
    op=''
    op += f'{ bold_white("Namespace:") } { bold_green(namespace) }\n'
    op += f'{ bold_white("Resources:") } { bold_blue( " ".join(resources) ) }\n'

    nodes = get_nodes()

    for resource in resources:
        #op += '\n'
        if resource.find("no") == 0:         op+='\n'+sprint_nodes()
        if resource.find("svc") == 0:        op+='\n'+sprint_services(namespace)
        if resource.find("service") == 0:    op+='\n'+sprint_services(namespace)
        if resource.find("deploy") == 0:     op+='\n'+sprint_deployments(namespace)
        if resource.find("rs") == 0:         op+='\n'+sprint_replica_sets(namespace)
        if resource.find("replicaset") == 0: op+='\n'+sprint_replica_sets(namespace)
        if resource.find("po") == 0:         op+='\n'+sprint_pods(namespace)
     
    if op != last_op:
        cls()
        print(op)
        last_op = op

    time.sleep(0.5)     # Sleep for 500 milliseconds
    #print(f"{bold('blue')}Resources: {" ".join(resources)}{colour('blue')}")

    #print(resources)
    #R=" ".join(resources)
    #print(R)


