#!/usr/bin/env python3

SHOW_TYPES=True

VERBOSE=False

#LATER: requires new fields
#def print_pvs(namespace='all'):  print(sprint_pvs(namespace))
#def sprint_pvcs(namespace):
#def print_pvcs(namespace='all'): print(sprint_pvcs(namespace))
#def sprint_pvs(namespace):

import sys, time
from kubernetes import client, config

# For timestamp handling:
from datetime import datetime

# Make sure ~/.kube/config is pointing to a valid cluster or kubernetes import will timeout ... after quite a while ...
config.load_kube_config()
#config.load_incluster_config()

# Get API clients:
corev1 = client.CoreV1Api()
appsv1 = client.AppsV1Api()
batchv1 = client.BatchV1Api()
batchv1beta1 = client.BatchV1beta1Api()

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

def die(msg):
    print(f"die: {msg}")
    sys.exit(1)

def sort_lines_by_age(op_lines, ages):
    sorted_op_lines = sorted(op_lines, key=lambda x: x['age'], reverse=True)
    retstr = "\n"
    for line in sorted_op_lines:
        retstr += line['line']
    return retstr

def setHMS(AGEsecs):
    OP=""

    try:
        if AGEsecs > 3600 * 24: # > 1d
            days = int(AGEsecs / 3600 / 24)
            AGEsecs = AGEsecs - (3600 * 24 * days)
            OP+=f"{days}d"
        if AGEsecs > 3600: # > 1h
            hours = int(AGEsecs / 3600)
            AGEsecs = AGEsecs - (3600 * hours)
            OP+=f"{hours:02d}h"
        if AGEsecs > 60: # > 1m
            mins = int(AGEsecs / 60)
            AGEsecs = AGEsecs - (60 * mins)
            OP+=f"{mins:02d}m"
        OP+=f"{AGEsecs:02}s"
        return OP
    except:
        return "-"

def get_age(i):
    creation_time = str(i.metadata.creation_timestamp)
    if '+00:00' in creation_time: creation_time = creation_time[ : creation_time.find('+00:00') ]

    try:
        d = datetime.strptime(creation_time, "%Y-%m-%d %H:%M:%S")
        AGE=time.mktime(d.timetuple())
        d = datetime.now()
        NOW=time.mktime(d.timetuple())
        AGE=NOW-AGE
        AGE=int(AGE) # Remove .0
        #AGE=AGE[:-2] # Remove .0
    except:
        AGE=0

    return AGE, setHMS(AGE)

def print_nodes(): print(sprint_nodes())

def sprint_nodes():
    type =  'node/' if SHOW_TYPES else ''

    ret = corev1.list_node(watch=False)
    if len(ret.items) == 0: return ''

    op_lines=[]; ages={}; idx=0
    for i in ret.items:
        node_ip   = i.status.addresses[0].address
        node_name = i.metadata.name

        taints = i.spec.taints
        if taints and len(taints) != 0:
            noexec=False
            for taint in taints:
                if hasattr(taint, 'effect') and taint.effect == 'NoExecute': noexec=True
            if noexec:
                node_name = red(node_name)
            else:
                node_name = yellow(node_name)

        AGE, AGE_HMS = get_age(i)
        LINE=f"{type}{node_name:12s} { green( node_ip ) :24s} {AGE_HMS}\n"
        op_lines.append({'age': AGE, 'line': LINE})

    return sort_lines_by_age(op_lines, ages)

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
    type =  'pod/' if SHOW_TYPES else ''

    if namespace == 'all':
        ret = corev1.list_pod_for_all_namespaces(watch=False)
    else:
        ret = corev1.list_namespaced_pod(watch=False, namespace=namespace)
    if len(ret.items) == 0: return ''

    op_lines=[]; ages={}; idx=0
    for i in ret.items:
        pod_name      = i.metadata.name
        pod_namespace = i.metadata.namespace
        pod_ip        = i.status.pod_ip
        host_ip       = i.status.host_ip
        host          = host_ip

        if pod_ip == None: pod_ip="-"
        if host   == None: host="-"

        if host_ip in nodes:
            host = nodes[host_ip]
            if   "ma" in host: host=cyan(host)
            elif "wo" in host: host=magenta(host)
            else:              pass

        phase=i.status.phase
        is_ready=False
        is_scheduled=False

        status = i.status.to_dict()
        if 'conditions' in status:
            if status['conditions']:
                for cond in status['conditions']:
                    if 'type' in cond:
                        ctype = cond['type']
                        cstatus = cond['status']
                        if ctype == 'Ready'        and cstatus == "True": is_ready=True
                        if ctype == 'PodScheduled' and cstatus == "True": is_scheduled=True

        info=''
        if is_scheduled and (not is_ready):
            try:
                container0 = status['container_statuses'][0] # !!
                info=container0['state']['terminated']['reason']
            except:
                try:
                    info=container0['state']['waiting']['reason']
                except:
                    info='NonReady'

        else:
            info=phase

        if info == "Running": info=green("Running")
        if info == "Complete": info=yellow("Running")

        if hasattr(i.metadata,'deletion_timestamp'):
            if i.metadata.deletion_timestamp: info = red("Terminating")

        AGE, AGE_HMS = get_age(i)

        if VERBOSE: # Checking for unset vars
            print(f"namespace={i.metadata.namespace:12s}")
            print(f"type/name={type}{i.metadata.name:32s}")
            print(f"info={info}")
            print(f"pod_ip/host={pod_ip:15s}/{host}\n")
            print(f"creation_time={creation_time}")
            print(f"AGE={AGE_HMS}\n")


        LINE = f"{i.metadata.namespace:12s} {type}{i.metadata.name:32s} {info} {pod_ip:15s}/{host:10s} {AGE_HMS}\n"
        op_lines.append({'age': AGE, 'line': LINE})

    return sort_lines_by_age(op_lines, ages)

def print_deployments(namespace='all'): print(sprint_deployments(namespace))

def sprint_deployments(namespace='all'):
    type =  'deploy/' if SHOW_TYPES else ''

    if namespace == 'all':
        ret = appsv1.list_deployment_for_all_namespaces(watch=False)
    else:
        ret = appsv1.list_namespaced_deployment(watch=False, namespace=namespace)
    if len(ret.items) == 0: return ''

    op_lines=[]; ages={}; idx=0
    for i in ret.items:
        spec=i.spec.replicas
        stat=i.status.ready_replicas
        if stat == spec:
            info=green(f'{stat}/{spec}')
        else:
            info=yellow(f'{stat}/{spec}')
        AGE, AGE_HMS = get_age(i)
        LINE = f"{type}{i.metadata.namespace:12s} {i.metadata.name:42s} {info} {AGE_HMS}\n"
        op_lines.append({'age': AGE, 'line': LINE})

    return sort_lines_by_age(op_lines, ages)

def print_daemon_sets(namespace='all'): print(sprint_daemon_sets(namespace))

def sprint_daemon_sets(namespace='all'):
    type =  'ds/' if SHOW_TYPES else ''

    if namespace == 'all':
        ret = appsv1.list_daemon_set_for_all_namespaces(watch=False)
    else:
        ret = appsv1.list_namespaced_daemon_set(watch=False, namespace=namespace)
    if len(ret.items) == 0: return ''

    op_lines=[]; ages={}; idx=0
    for i in ret.items:
        AGE, AGE_HMS = get_age(i)
        LINE = f"{type}{i.metadata.namespace:12s} {i.metadata.name:42s}\n"
        op_lines.append({'age': AGE, 'line': LINE})

    return sort_lines_by_age(op_lines, ages)

def print_stateful_sets(namespace='all'): print(sprint_stateful_sets(namespace))

def sprint_stateful_sets(namespace='all'):
    type =  'ss/' if SHOW_TYPES else ''

    if namespace == 'all':
        ret = appsv1.list_stateful_set_for_all_namespaces(watch=False)
    else:
        ret = appsv1.list_namespaced_stateful_set(watch=False, namespace=namespace)
    if len(ret.items) == 0: return ''

    op_lines=[]; ages={}; idx=0
    for i in ret.items:
        spec=i.spec.replicas
        stat=i.status.ready_replicas
        if stat == spec:
            info=green(f'{stat}/{spec}')
        else:
            info=yellow(f'{stat}/{spec}')
        AGE, AGE_HMS = get_age(i)
        LINE = f"{type}{i.metadata.namespace:12s} {i.metadata.name:42s} {info} {AGE_HMS}\n"
        op_lines.append({'age': AGE, 'line': LINE})

    return sort_lines_by_age(op_lines, ages)

def print_replica_sets(namespace='all'): print(sprint_stateful_sets(namespace))

def sprint_replica_sets(namespace='all'):
    type =  'rs/' if SHOW_TYPES else ''

    if namespace == 'all':
        ret = appsv1.list_replica_set_for_all_namespaces(watch=False)
    else:
        ret = appsv1.list_namespaced_replica_set(watch=False, namespace=namespace)
    if len(ret.items) == 0: return ''

    op_lines=[]; ages={}; idx=0
    for i in ret.items:
        spec=i.spec.replicas
        stat=i.status.ready_replicas
        if stat == spec:
            info=green(f'{stat}/{spec}')
        else:
            info=yellow(f'{stat}/{spec}')

        AGE, AGE_HMS = get_age(i)
        LINE = f"{type}{i.metadata.namespace:12s} {i.metadata.name:42s} {info:12s} {AGE_HMS}\n"
        op_lines.append({'age': AGE, 'line': LINE})

    return sort_lines_by_age(op_lines, ages)

def print_replica_sets(namespace='all'): print(sprint_replica_sets(namespace))

def sprint_replica_sets(namespace='all'):
    type =  'rs/' if SHOW_TYPES else ''

    if namespace == 'all':
        ret = appsv1.list_replica_set_for_all_namespaces(watch=False)
    else:
        ret = appsv1.list_namespaced_replica_set(watch=False, namespace=namespace)
    if len(ret.items) == 0: return ''

    op_lines=[]; ages={}; idx=0
    for i in ret.items:
        spec=i.spec.replicas
        stat=i.status.ready_replicas
        if stat == spec:
            info=green(f'{stat}/{spec}')
        else:
            info=yellow(f'{stat}/{spec}')
        AGE, AGE_HMS = get_age(i)
        LINE = f"{type}{i.metadata.namespace:12s} {i.metadata.name:42s} {info} {AGE_HMS}\n"
        op_lines.append({'age': AGE, 'line': LINE})

    return sort_lines_by_age(op_lines, ages)

def print_services(namespace='all'): print(sprint_services(namespace))

def sprint_services(namespace='all'):
    type =  'svc/' if SHOW_TYPES else ''

    if namespace == 'all':
        ret = corev1.list_service_for_all_namespaces(watch=False)
    else:
        ret = corev1.list_namespaced_service(watch=False, namespace=namespace)
    if len(ret.items) == 0: return ''

    op_lines=[]; ages={}; idx=0
    for i in ret.items:
        NPORT=""
        spec = i.spec.to_dict()
        #{'cluster_ip': '10.109.121.252', 'external_i_ps': None, 'external_name': None, 'external_traffic_policy': None, 'health_check_node_port': None, 'load_balancer_ip': None, 'load_balancer_source_ranges': None, 'ports': [{'name': None, 'node_port': None, 'port': 80, 'protocol': 'TCP', 'target_port': 80}], 'publish_not_ready_addresses': None, 'selector': {'app': 'ckad-demo-green'}, 'session_affinity': 'None', 'session_affinity_config': None, 'type': 'ClusterIP'}

        if spec and 'ports' in spec and spec['ports'] and 'node_port' in spec['ports'][0]:
            port0=spec['ports'][0]
            NPORT=f" NodePort:{port0['port']}:{port0['node_port']}"

        CIP=spec['cluster_ip']
        if not CIP: CIP=''

        POLICY=""
        AGE, AGE_HMS = get_age(i)
        LINE = f"{type}{i.metadata.namespace:12s} {i.metadata.name:42s} {CIP:15s}{NPORT:12s}{POLICY:8s} {AGE_HMS}\n"
        op_lines.append({'age': AGE, 'line': LINE})

    return sort_lines_by_age(op_lines, ages)

def print_jobs(namespace='all'): print(sprint_jobs(namespace))

def sprint_jobs(namespace='all'):
    type =  'job/' if SHOW_TYPES else ''

    if namespace == 'all':
        ret = batchv1.list_job_for_all_namespaces(watch=False)
    else:
        ret = batchv1.list_namespaced_job(watch=False, namespace=namespace)
    if len(ret.items) == 0: return ''

    op_lines=[]; ages={}; idx=0
    for i in ret.items:
        AGE, AGE_HMS = get_age(i)
        LINE = f"{type}{i.metadata.namespace:12s} {i.metadata.name:42s} {AGE_HMS}\n"
        op_lines.append({'age': AGE, 'line': LINE})

    return sort_lines_by_age(op_lines, ages)

def print_cron_jobs(namespace='all'): print(sprint_cron_jobs(namespace))

def sprint_cron_jobs(namespace='all'):
    type =  'cronjob/' if SHOW_TYPES else ''

    if namespace == 'all':
        ret = batchv1beta1.list_cron_job_for_all_namespaces(watch=False)
    else:
        ret = batchv1beta1.list_namespaced_cron_job(watch=False, namespace=namespace)
    if len(ret.items) == 0: return ''

    op_lines=[]; ages={}; idx=0
    for i in ret.items:
        AGE, AGE_HMS = get_age(i)
        LINE = f"{type}{i.metadata.namespace:12s} {i.metadata.name:42s} {AGE_HMS}\n"
        op_lines.append({'age': AGE, 'line': LINE})

    return sort_lines_by_age(op_lines, ages)

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

    print("\n======== [all namespaces] Listing stateful_sets:")
    print_stateful_sets()
    print("\n---- [namespace='default'] Listing stateful_sets:")
    print_stateful_sets(namespace='default')

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
    a+=1
    if arg == "-st":            SHOW_TYPES=True;  continue
    if arg == "-show-types":    SHOW_TYPES=True;  continue
    if arg == "-nst":           SHOW_TYPES=False; continue
    if arg == "-no-show-types": SHOW_TYPES=False; continue

    if arg == "-v": VERBOSE=True; continue

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

    resources.append( arg )

final_resources=[]
for reslist in resources:
    if "," in reslist:
        res = reslist.split(",")
        final_resources.extend(res)
    else:
        res = reslist
        final_resources.append(res)

resources=final_resources

if namespace == None: namespace=default_namespace
if namespace == "-": namespace="all"

if len(resources) == 0: resources = default_resources

print(f'namespace={namespace}')
print(f'resources={resources}')

last_op=''
while True:
    op=''
    op += f'{ bold_white("Namespace:") } { bold_green(namespace) }\n'
    op += f'{ bold_white("Resources:") } { bold_blue( " ".join(resources) ) }\n'

    nodes = get_nodes()

    for resource in resources:
        match=False

        if resource.find("no") == 0:
            match=True
            op+=sprint_nodes()

        if resource.find("all") == 0 or resource.find("nall") == 0:
            match=True
            if resource.find("nall") == 0:
                op+=sprint_nodes()
            op+=sprint_services(namespace)
            op+=sprint_deployments(namespace)
            op+=sprint_replica_sets(namespace)
            op+=sprint_stateful_sets(namespace)
            op+=sprint_pods(namespace)
            op+=sprint_jobs(namespace)
            op+=sprint_cron_jobs(namespace)

        if resource.find("svc") == 0 or resource.find("service") == 0:
            match=True
            op+=sprint_services(namespace)

        if resource.find("dep") == 0:
            match=True
            op+=sprint_deployments(namespace)
        if resource.find("ds") == 0 or resource.find("dset") == 0 or resource.find("daemonset") == 0:
            match=True
            op+=sprint_daemon_sets(namespace)
        if resource.find("rs") == 0 or resource.find("replicaset") == 0:
            match=True
            op+=sprint_replica_sets(namespace)
        if resource.find("ss") == 0 or resource.find("sts") == 0:
            match=True
            op+=sprint_stateful_sets(namespace)

        if resource.find("po") == 0:
            match=True
            op+=sprint_pods(namespace)

        if resource.find("job") == 0:
            match=True
            op+=sprint_jobs(namespace)
        if resource.find("cj") == 0 or resource.find("cron") == 0:
            match=True
            op+=sprint_cron_jobs(namespace)
        # LATER: if resource.find("pvc") == 0:        op+=sprint_pvcs(namespace)
        # LATER: if resource.find("pv") == 0:         op+=sprint_pvs(namespace)

        if not match:
            die(f"No match for resource type '{resource}'")

    if op != last_op:
        cls()
        print(op)
        last_op = op

    time.sleep(0.5)     # Sleep for 500 milliseconds


