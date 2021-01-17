#!/usr/bin/env python3

SHOW_TYPES=True

VERBOSE=False

NAME_FMT="32s"
INFO_FMT="60s"
NS_FMT="15s"

#default_resources=["pods"]
default_resources=["all"]

import os, sys, time
from kubernetes import client, config

# For timestamp handling:
from datetime import datetime
import json

## -- Get kubeconfig/cluster information: -------------------------

# Make sure ~/.kube/config is pointing to a valid cluster or kubernetes import will timeout ... after quite a while ...
HOME=os.getenv('HOME')
KUBECONFIG=os.getenv('KUBECONFIG')
DEFAULT_KUBECONFIG=HOME+'/.kube/config'

if KUBECONFIG == None:
    KUBECONFIG=DEFAULT_KUBECONFIG

#config.load_kube_config()
if os.path.exists(KUBECONFIG):
    print(f'Using KUBECONFIG={KUBECONFIG}')
    config.load_kube_config(KUBECONFIG)
else:
    print(f'No such kubeconfig file as "{KUBECONFIG}" - assuming in cluster')
    config.load_incluster_config()

#os.mkdir( '~/tmp', 0755 )
TMP_DIR = HOME + '/tmp'
if not os.path.exists(TMP_DIR): os.mkdir( TMP_DIR )

## -- Get context/namespace  information: -------------------------

contexts, active_context = config.list_kube_config_contexts()
# {'context': {'cluster': 'kubernetes', 'namespace': 'k8scenario', 'user': 'kubernetes-admin'}, 'name': 'k8scenario'}

default_namespace='default'
if 'namespace' in active_context['context']:
    default_namespace=active_context['context']['namespace']

#print(active_context)
context=active_context['name']
print(f'context={context} namespace={default_namespace}')

## -- Get API clients: --------------------------------------------

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
        return OP.strip('0') # Strip of any leading zero
    except:
        return "-"

def write_json(response, json_file):
    #def datetime_handler(x):
        #if isinstance(x, datetime.datetime):
            #return x.isoformat()
        #raise TypeError("Unknown type")

    #json_struct = json.dumps(response, default=datetime_handler, indent=2)
    json_struct = json.dumps(response, indent=2)
    Path(json_file).write_text(json_struct)

def write_json_items(items, file):
    loop=1
    for i in items:
        jfile=file.replace("N.json", f'{loop}.json')
        fd = open(jfile, 'w')
        fd.write(str(i))
        loop += 1
        #write_json(i, jfile)

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

def get_replicas_info(instance):
    spec=instance.spec.replicas
    stat=instance.status.ready_replicas
    if stat == spec:
        replicas_info=green(f'{stat}/{spec}')
    else:
        if stat == None: stat = 0
        replicas_info=yellow(f'{stat}/{spec}')
    return replicas_info

def print_nodes(): print(sprint_nodes())

def sprint_nodes():
    #type =  'node/' if SHOW_TYPES else ''
    type =  'nodes:' if SHOW_TYPES else ''

    ret = corev1.list_node(watch=False)
    if len(ret.items) == 0: return ''
    write_json_items(ret.items, TMP_DIR + '/nodesN.json')

    op_lines=[]; ages={}; idx=0

    max_name_len=0
    for i in ret.items:
        #print(max_name_len)
        node_name = i.metadata.name
        if len(node_name) > max_name_len: max_name_len=len(node_name)
        name_format=f'<{max_name_len+12}s'

    for i in ret.items:
        node_ip   = i.status.addresses[0].address
        node_name = i.metadata.name

        # Do node_name padding before adding ansi color chars:
        #node_name = node_name + '-------'; node_name = node_name[0:8]
        node_name = f'{node_name:{name_format}}'

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
        LINE=f"   {node_name:8s} { green( node_ip ) :24s} {AGE_HMS}\n"
        op_lines.append({'age': AGE, 'line': LINE})

    return type + sort_lines_by_age(op_lines, ages)

def get_nodes():
    nodes = {}

    ret = corev1.list_node(watch=False)
    for i in ret.items:
        node_ip   = i.status.addresses[0].address
        node_name = i.metadata.name
        nodes[node_ip] = node_name
    return nodes

def print_pvs(namespace='all'):  print(sprint_pvs(namespace))

def sprint_pvcs(namespace):
    type =  'persistentvolumeclaims:' if SHOW_TYPES else ''
    if namespace == 'all':
        ret = corev1.list_pvc_for_all_namespaces(watch=False)
    else:
        ret = corev1.list_namespaced_pvc(watch=False, namespace=namespace)
    if len(ret.items) == 0: return ''
    write_json_items(ret.items, TMP_DIR + '/pvcsN.json')

    pass

def print_pvcs(namespace='all'): print(sprint_pvcs(namespace))

def sprint_pvs(namespace):
    type =  'persistentvolumes:' if SHOW_TYPES else ''
    ret = corev1.list_pv(watch=False)
    if len(ret.items) == 0: return ''
    write_json_items(ret.items, TMP_DIR + '/pvsN.json')

    pass

def print_pods(namespace='all'): print(sprint_pods(namespace)[:-1])

def sprint_pods(namespace='all'):
    #type =  'pod/' if SHOW_TYPES else ''
    type =  'pods:' if SHOW_TYPES else ''

    if namespace == 'all':
        ret = corev1.list_pod_for_all_namespaces(watch=False)
    else:
        ret = corev1.list_namespaced_pod(watch=False, namespace=namespace)
    if len(ret.items) == 0: return ''
    write_json_items(ret.items, TMP_DIR + '/podsN.json')

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
            if host.find("ma") == 0: host=cyan(host) # Colour master nodes

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

        try:
            cexpected=len( status['container_statuses'] )
        except:
            cexpected=0
        cready=0
        des_act=f'{cready}/{cexpected}'

        if is_scheduled and is_ready:
            try:
                for c in status['container_statuses']:
                    if 'ready' in c and c['ready'] == True: cready+=1
                des_act=f'{cready}/{cexpected} '
            except:
                des_act=f'{cready}/{cexpected} '
        if cready < cexpected: des_act=yellow(des_act)

        if info == "Running": info=green("Running")
        if info == "Complete": info=yellow("Running")

        if hasattr(i.metadata,'deletion_timestamp'):
            if i.metadata.deletion_timestamp: info = red("Terminating")

        AGE, AGE_HMS = get_age(i)

        if VERBOSE: # Checking for unset vars
            print(f"namespace={i.metadata.namespace:{NS_FMT}}")
            print(f"type/name={type}{i.metadata.name:{NAME_FMT}}")
            print(f"info={info}")
            print(f"pod_ip/host={pod_ip:15s}/{host}\n")
            print(f"creation_time={creation_time}")
            print(f"AGE={AGE_HMS}\n")

        ns_info=''
        if namespace == 'all':
            ns_info=f'[{i.metadata.namespace:{NS_FMT}}] '

        LINE = f"  {ns_info} {i.metadata.name:{NAME_FMT}} {des_act} {info:20s} {pod_ip:15s}/{host:10s} {AGE_HMS}\n"
        op_lines.append({'age': AGE, 'line': LINE})

    #return (type + sort_lines_by_age(op_lines, ages))[:-1]
    return (type + sort_lines_by_age(op_lines, ages)).rstrip()

def print_deployments(namespace='all'): print(sprint_deployments(namespace))

def sprint_deployments(namespace='all'):
    #type =  'deploy' if SHOW_TYPES else ''
    type =  'deployments:' if SHOW_TYPES else ''

    if namespace == 'all':
        ret = appsv1.list_deployment_for_all_namespaces(watch=False)
    else:
        ret = appsv1.list_namespaced_deployment(watch=False, namespace=namespace)
    if len(ret.items) == 0: return ''
    write_json_items(ret.items, TMP_DIR + '/deploysN.json')

    op_lines=[]; ages={}; idx=0
    for i in ret.items:
        info=get_replicas_info(i)
        AGE, AGE_HMS = get_age(i)

        ns_info=''
        if namespace == 'all':
            ns_info=f'[{i.metadata.namespace:{NS_FMT}}] '

        #LINE = f"{type}{i.metadata.namespace:{NS_FMT}} {i.metadata.name:{NAME_FMT}} {info} {AGE_HMS}\n"
        LINE = f"  {ns_info} {i.metadata.name:{NAME_FMT}} {info:{INFO_FMT}} {AGE_HMS}\n"
        op_lines.append({'age': AGE, 'line': LINE})

    #return (type + sort_lines_by_age(op_lines, ages))[:-1]
    #return (type + sort_lines_by_age(op_lines, ages)).rstrip()
    return type + sort_lines_by_age(op_lines, ages)

def print_daemon_sets(namespace='all'): print(sprint_daemon_sets(namespace))

def sprint_daemon_sets(namespace='all'):
    #type =  'ds/' if SHOW_TYPES else ''
    type =  'daemonsets:' if SHOW_TYPES else ''

    if namespace == 'all':
        ret = appsv1.list_daemon_set_for_all_namespaces(watch=False)
    else:
        ret = appsv1.list_namespaced_daemon_set(watch=False, namespace=namespace)
    if len(ret.items) == 0: return ''
    write_json_items(ret.items, TMP_DIR + '/dsetsN.json')

    op_lines=[]; ages={}; idx=0
    for i in ret.items:
        AGE, AGE_HMS = get_age(i)

        ns_info=''
        if namespace == 'all':
            ns_info=f'[{i.metadata.namespace:{NS_FMT}}] '

        LINE = f"  {ns_info} {i.metadata.name:{NAME_FMT}}\n"
        op_lines.append({'age': AGE, 'line': LINE})

    return type + sort_lines_by_age(op_lines, ages)

def print_stateful_sets(namespace='all'): print(sprint_stateful_sets(namespace))

def sprint_stateful_sets(namespace='all'):
    #type =  'ss/' if SHOW_TYPES else ''
    type =  'statefulsets:' if SHOW_TYPES else ''

    if namespace == 'all':
        ret = appsv1.list_stateful_set_for_all_namespaces(watch=False)
    else:
        ret = appsv1.list_namespaced_stateful_set(watch=False, namespace=namespace)
    if len(ret.items) == 0: return ''
    write_json_items(ret.items, TMP_DIR + '/ssetsN.json')

    op_lines=[]; ages={}; idx=0
    for i in ret.items:
        info=get_replicas_info(i)
        AGE, AGE_HMS = get_age(i)

        ns_info=''
        if namespace == 'all':
            ns_info=f'[{i.metadata.namespace:{NS_FMT}}] '

        LINE = f"  {ns_info} {i.metadata.name:{NAME_FMT}} {info:56} {AGE_HMS}\n"
        op_lines.append({'age': AGE, 'line': LINE})

    return type + sort_lines_by_age(op_lines, ages)

def print_replica_sets(namespace='all'): print(sprint_replica_sets(namespace))

def sprint_replica_sets(namespace='all'):
    #type =  'rs/' if SHOW_TYPES else ''
    type =  'replicasets:' if SHOW_TYPES else ''

    if namespace == 'all':
        ret = appsv1.list_replica_set_for_all_namespaces(watch=False)
    else:
        ret = appsv1.list_namespaced_replica_set(watch=False, namespace=namespace)
    if len(ret.items) == 0: return ''
    write_json_items(ret.items, TMP_DIR + '/repsetsN.json')

    op_lines=[]; ages={}; idx=0
    for i in ret.items:
        info=get_replicas_info(i)
        AGE, AGE_HMS = get_age(i)

        ns_info=''
        if namespace == 'all':
            ns_info=f'[{i.metadata.namespace:{NS_FMT}}] '

        #LINE = f"{type}{i.metadata.namespace:{NS_FMT}} {i.metadata.name:{NAME_FMT}} {info:12s} {AGE_HMS}\n"
        LINE = f"  {ns_info} {i.metadata.name:{NAME_FMT}} {info:{INFO_FMT}} {AGE_HMS}\n"
        op_lines.append({'age': AGE, 'line': LINE})

    return type + sort_lines_by_age(op_lines, ages)

def print_services(namespace='all'): print(sprint_services(namespace))

def sprint_services(namespace='all'):
    #type =  'svc/' if SHOW_TYPES else ''
    type =  'services:' if SHOW_TYPES else ''

    if namespace == 'all':
        ret = corev1.list_service_for_all_namespaces(watch=False)
    else:
        ret = corev1.list_namespaced_service(watch=False, namespace=namespace)
    if len(ret.items) == 0: return ''
    write_json_items(ret.items, TMP_DIR + '/servicesN.json')

    op_lines=[]; ages={}; idx=0
    for i in ret.items:
        NPORT=""
        spec = i.spec.to_dict()
        #print(spec); die("X");
        #{'cluster_ip': '10.109.121.252', 'external_ips': None, 'external_name': None, 'external_traffic_policy': None, 'health_check_node_port': None, 'load_balancer_ip': None, 'load_balancer_source_ranges': None,
        #  'ports': [{'name': None, 'node_port': None, 'port': 80, 'protocol': 'TCP', 'target_port': 80}],
        #  'publish_not_ready_addresses': None, 'selector': {'app': 'ckad-demo-green'}, 'session_affinity': 'None', 'session_affinity_config': None, 'type': 'ClusterIP'}

        SVC_TYPE=spec['type']
        EXT_IPS=spec['external_i_ps']
        if not EXT_IPS: EXT_IPS='Pending' # Needs checking, is it this field or load_balancer_ip ??

        if spec and 'ports' in spec and spec['ports'] and 'node_port' in spec['ports'][0]:
            port0=spec['ports'][0]
            if 'node_port' in port0 and port0['node_port'] != None:
                PORT=f" {port0['port']}:{port0['node_port']}"
            else:
                PORT=f" {port0['port']}"
            PORT += f"/{port0['protocol']}"

        CIP=spec['cluster_ip']
        if not CIP: CIP=''

        POLICY=""
        AGE, AGE_HMS = get_age(i)

        ns_info=''
        if namespace == 'all':
            ns_info=f'[{i.metadata.namespace:{NS_FMT}}] '

        LINE = f"  {ns_info} {i.metadata.name:{NAME_FMT}} {CIP:14s} {SVC_TYPE:12s} {EXT_IPS:15s} {PORT:14s}{POLICY:8s} {AGE_HMS}\n"
        op_lines.append({'age': AGE, 'line': LINE})

    return type + sort_lines_by_age(op_lines, ages)

def print_jobs(namespace='all'): print(sprint_jobs(namespace))

def sprint_jobs(namespace='all'):
    #type =  'job/' if SHOW_TYPES else ''
    type =  'jobs:' if SHOW_TYPES else ''

    if namespace == 'all':
        ret = batchv1.list_job_for_all_namespaces(watch=False)
    else:
        ret = batchv1.list_namespaced_job(watch=False, namespace=namespace)
    if len(ret.items) == 0: return ''
    write_json_items(ret.items, TMP_DIR + '/jobsN.json')

    op_lines=[]; ages={}; idx=0
    for i in ret.items:
        AGE, AGE_HMS = get_age(i)

        ns_info=''
        if namespace == 'all':
            ns_info=f'[{i.metadata.namespace:{NS_FMT}}] '

        LINE = f"  {ns_info} {i.metadata.name:{NAME_FMT}} {AGE_HMS}\n"
        op_lines.append({'age': AGE, 'line': LINE})

    return type + sort_lines_by_age(op_lines, ages)

def print_cron_jobs(namespace='all'): print(sprint_cron_jobs(namespace))

def sprint_cron_jobs(namespace='all'):
    #type =  'cronjob/' if SHOW_TYPES else ''
    type =  'cronjobs:' if SHOW_TYPES else ''

    if namespace == 'all':
        ret = batchv1beta1.list_cron_job_for_all_namespaces(watch=False)
    else:
        ret = batchv1beta1.list_namespaced_cron_job(watch=False, namespace=namespace)
    if len(ret.items) == 0: return ''
    write_json_items(ret.items, TMP_DIR + '/cronjobsN.json')

    op_lines=[]; ages={}; idx=0
    for i in ret.items:
        AGE, AGE_HMS = get_age(i)
        ns_info=''
        if namespace == 'all':
            ns_info=f'[{i.metadata.namespace:{NS_FMT}}] '

        LINE = f"{ns_info} {i.metadata.name:{NAME_FMT}} {AGE_HMS}\n"
        op_lines.append({'age': AGE, 'line': LINE})

    return type + sort_lines_by_age(op_lines, ages)

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

# Clears but keeps at bottom of screeen:
#def cls(): print(chr(27) + "[2J")
# Clears and positions at top of screeen:
#def cls(): print('\033[H\033[J')
def cls(): sys.stdout.write('\033[H\033[J')

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

    if arg == "-A":
        namespace="-"
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
if namespace == "-":  namespace="all"

if len(resources) == 0: resources = default_resources

full_context=f'{ bold_white("Context:") } { bold_green(context) } / { bold_white("Namespace:") } { bold_green(namespace) } / { bold_white("Resources:") } { bold_green(resources) }\n'
print(f'full_context={full_context}')

last_op=''
while True:
    op=''
    full_context=f'{ bold_white("Context:") } { bold_green(context) } / { bold_white("Namespace:") } { bold_green(namespace) } / { bold_white("Resources:") } { bold_green(resources) }\n'
    op += full_context
    #op += f'{ bold_white("Resources:") } { bold_blue( " ".join(resources) ) }\n'

    #if namespace = 'all': NS_FMT=set_ns_fmt()

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
        if resource.find("pvc") == 0:
            match=True
            op+=sprint_pvcs(namespace)
        if resource.find("pv") == 0:
            match=True
            op+=sprint_pvs(namespace)

        if not match:
            die(f"No match for resource type '{resource}'")

    if op != last_op:
        cls()
        print(op)
        last_op = op

    time.sleep(0.5)     # Sleep for 500 milliseconds


