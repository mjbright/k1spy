#!/usr/bin/env python3

'''
    TUI dashboard for Kubernetes resources
    Example of use of kubernetes python module
'''

import os
import sys
import time
# For timestamp handling:
from datetime import datetime
import json

from kubernetes import client, config

NAME_FMT="32s"
INFO_FMT="60s"
NS_FMT="15s"

SHOW_TYPES=False
VERBOSE=False
nodes=[]
resources=[]
namespace='default'

#default_resources=["pods"]
default_resources=["all"]

## -- Get kubeconfig/cluster information: -------------------------

# Make sure ~/.kube/config is pointing to a valid cluster
HOME=os.getenv('HOME')
KUBECONFIG=os.getenv('KUBECONFIG')
DEFAULT_KUBECONFIG=HOME+'/.kube/config'

if KUBECONFIG is None:
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
if not os.path.exists(TMP_DIR):
    os.mkdir( TMP_DIR )

## -- Get context/namespace  information: -------------------------

contexts, active_context = config.list_kube_config_contexts()
# {'context': {'cluster': 'kubernetes', 'namespace': 'k8scenario', 'user': 'kubernetes-admin'},
#  'name': 'k8scenario'}

DEFAULT_NAMESPACE='default'
if 'namespace' in active_context['context']:
    DEFAULT_NAMESPACE=active_context['context']['namespace']

#print(active_context)
context=active_context['name']
print(f'context={context} namespace={DEFAULT_NAMESPACE}')

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

def black(msg):
    ''' return black ansi-coloured 'msg' text'''
    return f"{BLACK}{msg}{RESET}"
def red(msg):
    ''' return red   ansi-coloured 'msg' text'''
    return f"{RED}{msg}{RESET}"
def green(msg):
    ''' return green ansi-coloured 'msg' text'''
    return f"{GREEN}{msg}{RESET}"
def yellow(msg):
    ''' return yellow ansi-coloured 'msg' text'''
    return f"{YELLOW}{msg}{RESET}"
def blue(msg):
    ''' return blue  ansi-coloured 'msg' text'''
    return f"{BLUE}{msg}{RESET}"
def magenta(msg):
    ''' return magenta ansi-coloured 'msg' text'''
    return f"{MAGENTA}{msg}{RESET}"
def cyan(msg):
    ''' return cyan  ansi-coloured 'msg' text'''
    return f"{CYAN}{msg}{RESET}"
def white(msg):
    ''' return white ansi-coloured 'msg' text'''
    return f"{WHITE}{msg}{RESET}"
def underline(msg):
    ''' return ansi-underlined 'msg' text'''
    return f"{UNDERLINE}{msg}{RESET}"
def reset(msg):
    ''' reset ansi-colouring before 'msg' text'''
    return f"{RESET}{msg}{RESET}"

def bold_black(msg):
    ''' return bold-black ansi-coloured 'msg' text'''
    return f"{BOLD_BLACK}{msg}{RESET}"
def bold_red(msg):
    ''' return bold-red   ansi-coloured 'msg' text'''
    return f"{BOLD_RED}{msg}{RESET}"
def bold_green(msg):
    ''' return bold-green ansi-coloured 'msg' text'''
    return f"{BOLD_GREEN}{msg}{RESET}"
def bold_yellow(msg):
    ''' return bold-yellow ansi-coloured 'msg' text'''
    return f"{BOLD_YELLOW}{msg}{RESET}"
def bold_blue(msg):
    ''' return bold-blue  ansi-coloured 'msg' text'''
    return f"{BOLD_BLUE}{msg}{RESET}"
def bold_magenta(msg):
    ''' return bold-magenta ansi-coloured 'msg' text'''
    return f"{BOLD_MAGENTA}{msg}{RESET}"
def bold_cyan(msg):
    ''' return bold-cyan  ansi-coloured 'msg' text'''
    return f"{BOLD_CYAN}{msg}{RESET}"
def bold_white(msg):
    ''' return bold-white ansi-coloured 'msg' text'''
    return f"{BOLD_WHITE}{msg}{RESET}"

#print(red("Hello"),"there",blue("how"),"are you?")
#print(underline("Hello"),"there",green("how"),yellow("are you?"))

#= END OF === COLOUR DEFINITIONS ==============================

## -- Funcs: ---------------------------------------------------

def die(msg):
    ''' exit after printing bold-red error 'msg' text'''
    print(f"die: { bold_red(msg) }")
    sys.exit(1)

def sort_lines_by_age(op_lines):
    ''' sort 'op_lines' list using 'age' attribute of each line '''
    sorted_op_lines = sorted(op_lines, key=lambda x: x['age'], reverse=True)
    retstr = "\n"
    for line in sorted_op_lines:
        retstr += line['line']
    return retstr

def set_hms(age_secs):
    ''' Build up a days-hours-mins-secs from provided {age_sec} secs '''
    output=""

    try:
        if age_secs > 3600 * 24: # > 1d
            days = int(age_secs / 3600 / 24)
            age_secs = age_secs - (3600 * 24 * days)
            output+=f"{days}d"
        if age_secs > 3600: # > 1h
            hours = int(age_secs / 3600)
            age_secs = age_secs - (3600 * hours)
            output+=f"{hours:02d}h"
        if age_secs > 60: # > 1m
            mins = int(age_secs / 60)
            age_secs = age_secs - (60 * mins)
            output+=f"{mins:02d}m"
        output+=f"{age_secs:02}s"
        return output.strip('0') # Strip of any leading zero
    except:
        return "-"

def write_json(response, json_file):
    ''' Write dump json {response} to {json_file} '''
    with open(json_file, "w") as write_file:
        json.dump(response, write_file, indent=2)

def write_json_items(items, file):
    ''' Write each json {item} to {file} '''
    loop=1
    for i in items:
        jfile=file.replace("N.json", f'{loop}.json')
        filed = open(jfile, 'w')
        filed.write(str(i))
        loop += 1

def get_age(i):
    ''' obtain {creation_time} age from {i.metadata} '''
    creation_time = str(i.metadata.creation_timestamp)
    if '+00:00' in creation_time:
        creation_time = creation_time[ : creation_time.find('+00:00') ]

    try:
        time_str = datetime.strptime(creation_time, "%Y-%m-%d %H:%M:%S")
        age_secs=time.mktime(time_str.timetuple())

        time_str = datetime.now()
        now_secs=time.mktime(time_str.timetuple())

        age_secs=now_secs - age_secs
        age_secs=int(age_secs)
    except:
        age_secs=0

    return age_secs, set_hms(age_secs)

def get_replicas_info(instance):
    ''' get info about pod replicas for controller instance '''
    spec=instance.spec.replicas
    stat=instance.status.ready_replicas
    if stat == spec:
        replicas_info=green(f'{stat}/{spec}')
    else:
        if stat is None:
            stat = 0
        replicas_info=yellow(f'{stat}/{spec}')
    return replicas_info

def print_nodes():
    ''' print resource info '''
    print(sprint_nodes())

def sprint_nodes():
    ''' build single-line representing resource info '''
    res_type =  'nodes:' if SHOW_TYPES else ''

    ret = corev1.list_node(watch=False)
    if len(ret.items) == 0:
        return ''

    write_json_items(ret.items, TMP_DIR + '/nodesN.json')

    op_lines=[]

    max_name_len=0
    for i in ret.items:
        node_name = i.metadata.name
        if len(node_name) > max_name_len:
            max_name_len=len(node_name)

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
                if hasattr(taint, 'effect') and taint.effect == 'NoExecute':
                    noexec=True
            if noexec:
                node_name = red(node_name)
            else:
                node_name = yellow(node_name)

        age, age_hms = get_age(i)
        line=f"   {node_name:8s} { green( node_ip ) :24s} {age_hms}\n"
        op_lines.append({'age': age, 'line': line})

    return res_type + sort_lines_by_age(op_lines)

def get_nodes():
    ''' get list of node resources '''
    l_nodes = {}

    ret = corev1.list_node(watch=False)
    for i in ret.items:
        node_ip   = i.status.addresses[0].address
        node_name = i.metadata.name
        l_nodes[node_ip] = node_name
    return l_nodes

def print_pvcs(p_namespace='all'):
    ''' print resource info '''
    print(sprint_pvcs(p_namespace))

def sprint_pvcs(p_namespace):
    ''' build single-line representing resource info '''
    res_type =  'persistentvolumeclaims:' if SHOW_TYPES else ''
    if p_namespace == 'all':
        ret = corev1.list_persistent_volume_claim_for_all_namespaces(watch=False)
    else:
        ret = corev1.list_namespaced_persistent_volume_claim(watch=False, namespace=p_namespace)

    if len(ret.items) == 0:
        return ''

    write_json_items(ret.items, TMP_DIR + '/pvcsN.json')

    max_name_len=5
    for i in ret.items:
        if len(i.metadata.name) > max_name_len:
            max_name_len=len(i.metadata.name)

    name_fmt=f'{max_name_len+1}s'

    op_lines=[]
    for i in ret.items:
        age, age_hms = get_age(i)

        ns_info=''
        if p_namespace == 'all':
            ns_info=f'[{i.metadata.namespace:{NS_FMT}}] '

        access_modes=",".join(i.status.access_modes)

        #print(i.spec)
        line = f'  {ns_info} {i.metadata.name:{name_fmt}} {i.status.capacity["storage"]:6s} {access_modes} {i.status.phase:10s} {age_hms}\n'

        op_lines.append( {'age': age, 'line': line} )

    return res_type + sort_lines_by_age(op_lines)
    #return (res_type + sort_lines_by_age(op_lines)).rstrip()

'''
    NAME                              STATUS   VOLUME   CAPACITY   ACCESS MODES   STORAGECLASS   AGE
    persistentvolumeclaim/myclaim-1   Bound    pv0003   4Gi        RWO                           10m
'''

def print_pvs(p_namespace='all'):
    ''' print resource info '''
    print(sprint_pvs(p_namespace))

def sprint_pvs(p_namespace):
    ''' build single-line representing resource info '''
    res_type =  'persistentvolumes:' if SHOW_TYPES else ''
    ret = corev1.list_persistent_volume(watch=False)

    if len(ret.items) == 0:
        return ''

    write_json_items(ret.items, TMP_DIR + '/pvsN.json')

    max_name_len=5
    max_claim_len=5
    for i in ret.items:
        if len(i.metadata.name) > max_name_len:
            max_name_len=len(i.metadata.name)
        if i.spec.claim_ref:
            claimRef=i.spec.claim_ref
            claim=f'{claimRef.namespace}/{claimRef.name}'
            if len(claim) > max_claim_len:
                max_claim_len=len(claim)

    name_fmt=f'{max_name_len+1}s'
    name_claim_fmt=f'{max_claim_len+1}s'

    op_lines=[]
    for i in ret.items:
        age, age_hms = get_age(i)

        ns_info=''
        if p_namespace == 'all':
            ns_info=f'[{i.metadata.namespace:{NS_FMT}}] '

        #print(i.spec)
        policy=i.spec.persistent_volume_reclaim_policy
        access_modes=",".join(i.spec.access_modes)

        #line = f'  {ns_info} {i.metadata.name:{NAME_FMT}} {i.spec.capacity.storage} {i.spec.accessModes} {i.status.phase} {i.spec.persistentVolumeReclaimPolicy}\n'

        claim=''
        if i.spec.claim_ref:
            claimRef=i.spec.claim_ref
            claim=f'{claimRef.namespace}/{claimRef.name}'

        line = f'  {ns_info} {i.metadata.name:{name_fmt}} {i.spec.capacity["storage"]:6s} {access_modes} {i.status.phase:10s} {claim:{name_claim_fmt}} {policy} {age_hms}\n'
        op_lines.append( {'age': age, 'line': line} )

    return res_type + sort_lines_by_age(op_lines)
    #return (res_type + sort_lines_by_age(op_lines)).rstrip()

def print_pods(p_namespace='all'):
    ''' print resource info '''
    print(sprint_pods(p_namespace)[:-1])

def sprint_pods(p_namespace='all'):
    ''' build single-line representing resource info '''
    res_type =  'pods:' if SHOW_TYPES else ''

    if p_namespace == 'all':
        ret = corev1.list_pod_for_all_namespaces(watch=False)
    else:
        ret = corev1.list_namespaced_pod(watch=False, namespace=p_namespace)

    if len(ret.items) == 0:
        return ''

    write_json_items(ret.items, TMP_DIR + '/podsN.json')

    op_lines=[]
    for i in ret.items:
        op_lines.append( get_pod_info(i, res_type, p_namespace) )

    return (res_type + sort_lines_by_age(op_lines)).rstrip()

def get_pod_host_info(i):
    ''' Get pod_ip and coloured host name (yellow if master node) '''
    pod_ip        = i.status.pod_ip
    host_ip       = i.status.host_ip
    host          = host_ip

    if pod_ip is None:
        pod_ip="-"
    if host   is None:
        host="-"

    if host_ip in nodes:
        host = nodes[host_ip]
        if host.find("ma") == 0:
            host=cyan(host) # Colour master nodes

    return(pod_ip, host)

def get_pod_scheduling_status(i):
    ''' Obtain pod_scheduling_status: from conditions '''
    is_ready=False
    is_scheduled=False

    status = i.status.to_dict()
    if 'conditions' in status:
        if status['conditions']:
            for cond in status['conditions']:
                if 'type' in cond:
                    ctype = cond['type']
                    cstatus = cond['status']
                    if ctype == 'Ready'        and cstatus == "True":
                        is_ready=True
                    if ctype == 'PodScheduled' and cstatus == "True":
                        is_scheduled=True


    desired_actual_c = get_pod_desired_actual(status, is_ready, is_scheduled)
    return (status, is_ready, is_scheduled, desired_actual_c)

def get_pod_desired_actual(status, is_ready, is_scheduled):
    ''' Obtain desired/actual containers '''

    cexpected=0
    if 'container_statuses' in status:
        cexpected=len( status['container_statuses'] )

    cready=0
    desired_actual_c=f'{cready}/{cexpected}'

    if is_scheduled and is_ready:
        try:
            for cont_status in status['container_statuses']:
                if 'ready' in cont_status and cont_status['ready']:
                    cready+=1
            desired_actual_c=f'{cready}/{cexpected} '
        except:
            desired_actual_c=f'{cready}/{cexpected} '

    if cready < cexpected:
        desired_actual_c=yellow(desired_actual_c)

    return desired_actual_c

def get_pod_status(i):
    ''' Obtain pod_status: desired/actual containers and status '''
    phase=i.status.phase

    ret_status=''
    ( status, is_ready, is_scheduled, desired_actual_c ) = get_pod_scheduling_status(i)

    if is_scheduled and (not is_ready):
        try:
            container0 = status['container_statuses'][0] # !!
            ret_status=container0['state']['terminated']['reason']
        except:
            try:
                ret_status=container0['state']['waiting']['reason']
            except:
                ret_status='NonReady'
    else:
        ret_status=phase

    if ret_status == "Running":
        ret_status=green("Running")

    if ret_status == "Complete":
        ret_status=yellow("Running")

    if hasattr(i.metadata,'deletion_timestamp'):
        if i.metadata.deletion_timestamp:
            ret_status = red("Terminating")

    return (desired_actual_c, ret_status)

def get_pod_info(i, res_type, p_namespace='all'):
    ''' Obtain pod_info as a line and age from instance '''

    (pod_ip, host) = get_pod_host_info(i)
    (desired_actual_c, pod_status) = get_pod_status(i)
    age, age_hms = get_age(i)

    if VERBOSE: # Checking for unset vars
        print(f"namespace={i.metadata.namespace:{NS_FMT}}")
        print(f"type/name={res_type}{i.metadata.name:{NAME_FMT}}")
        print(f"pod_status={pod_status}")
        print(f"pod_ip/host={pod_ip:15s}/{host}\n")
        print(f"creation_time={i.metadata.creation_time}")
        print(f"age={age_hms}\n")

    ns_info=''
    if p_namespace == 'all':
        ns_info=f'[{i.metadata.namespace:{NS_FMT}}] '

    pod_host_age = f'{pod_ip:15s}/{host:10s} {age_hms}'
    pod_info = f'{pod_status:20s} {pod_host_age}'
    line = f'  {ns_info} {i.metadata.name:{NAME_FMT}} {desired_actual_c} {pod_info}\n'

    return {'age': age, 'line': line}

def print_deployments(p_namespace='all'):
    ''' print resource info '''
    print(sprint_deployments(p_namespace))

def sprint_deployments(p_namespace='all'):
    ''' build single-line representing resource info '''
    res_type =  'deployments:' if SHOW_TYPES else ''

    if p_namespace == 'all':
        ret = appsv1.list_deployment_for_all_namespaces(watch=False)
    else:
        ret = appsv1.list_namespaced_deployment(watch=False, namespace=p_namespace)

    if len(ret.items) == 0:
        return ''

    write_json_items(ret.items, TMP_DIR + '/deploysN.json')

    op_lines=[]
    for i in ret.items:
        info=get_replicas_info(i)
        age, age_hms = get_age(i)

        ns_info=''
        if p_namespace == 'all':
            ns_info=f'[{i.metadata.namespace:{NS_FMT}}] '

        line = f"  {ns_info} {i.metadata.name:{NAME_FMT}} {info:{INFO_FMT}} {age_hms}\n"
        op_lines.append({'age': age, 'line': line})

    return res_type + sort_lines_by_age(op_lines)

def print_daemon_sets(p_namespace='all'):
    ''' print resource info '''
    print(sprint_daemon_sets(p_namespace))

def sprint_daemon_sets(p_namespace='all'):
    ''' build single-line representing resource info '''
    #res_type =  'ds/' if SHOW_TYPES else ''
    res_type =  'daemonsets:' if SHOW_TYPES else ''

    if p_namespace == 'all':
        ret = appsv1.list_daemon_set_for_all_namespaces(watch=False)
    else:
        ret = appsv1.list_namespaced_daemon_set(watch=False, namespace=p_namespace)
    if len(ret.items) == 0:
        return ''
    write_json_items(ret.items, TMP_DIR + '/dsetsN.json')

    op_lines=[]
    for i in ret.items:
        age, age_hms = get_age(i)

        ns_info=''
        if p_namespace == 'all':
            ns_info=f'[{i.metadata.namespace:{NS_FMT}}] '

        line = f"  {ns_info} {i.metadata.name:{NAME_FMT}} {age_hms}\n"
        op_lines.append({'age': age, 'line': line})

    return res_type + sort_lines_by_age(op_lines)

def print_stateful_sets(p_namespace='all'):
    ''' print resource info '''
    print(sprint_stateful_sets(p_namespace))

def sprint_stateful_sets(p_namespace='all'):
    ''' build single-line representing resource info '''
    #res_type =  'ss/' if SHOW_TYPES else ''
    res_type =  'statefulsets:' if SHOW_TYPES else ''

    if p_namespace == 'all':
        ret = appsv1.list_stateful_set_for_all_namespaces(watch=False)
    else:
        ret = appsv1.list_namespaced_stateful_set(watch=False, namespace=p_namespace)
    if len(ret.items) == 0:
        return ''
    write_json_items(ret.items, TMP_DIR + '/ssetsN.json')

    op_lines=[]
    for i in ret.items:
        info=get_replicas_info(i)
        age, age_hms = get_age(i)

        ns_info=''
        if p_namespace == 'all':
            ns_info=f'[{i.metadata.namespace:{NS_FMT}}] '

        line = f"  {ns_info} {i.metadata.name:{NAME_FMT}} {info:56} {age_hms}\n"
        op_lines.append({'age': age, 'line': line})

    return res_type + sort_lines_by_age(op_lines)

def print_replica_sets(p_namespace='all'):
    ''' print resource info '''
    print(sprint_replica_sets(p_namespace))

def sprint_replica_sets(p_namespace='all'):
    ''' build single-line representing resource info '''
    #res_type =  'rs/' if SHOW_TYPES else ''
    res_type =  'replicasets:' if SHOW_TYPES else ''

    if p_namespace == 'all':
        ret = appsv1.list_replica_set_for_all_namespaces(watch=False)
    else:
        ret = appsv1.list_namespaced_replica_set(watch=False, namespace=p_namespace)
    if len(ret.items) == 0:
        return ''
    write_json_items(ret.items, TMP_DIR + '/repsetsN.json')

    op_lines=[]
    for i in ret.items:
        info=get_replicas_info(i)
        age, age_hms = get_age(i)

        ns_info=''
        if p_namespace == 'all':
            ns_info=f'[{i.metadata.namespace:{NS_FMT}}] '

        line = f"  {ns_info} {i.metadata.name:{NAME_FMT}} {info:{INFO_FMT}} {age_hms}\n"
        op_lines.append({'age': age, 'line': line})

    return res_type + sort_lines_by_age(op_lines)

def print_services(p_namespace='all'):
    ''' print resource info '''
    print(sprint_services(p_namespace))

def sprint_services(p_namespace='all'):
    ''' build single-line representing resource info '''
    res_type =  'services:' if SHOW_TYPES else ''

    if p_namespace == 'all':
        ret = corev1.list_service_for_all_namespaces(watch=False)
    else:
        ret = corev1.list_namespaced_service(watch=False, namespace=p_namespace)
    if len(ret.items) == 0:
        return ''
    write_json_items(ret.items, TMP_DIR + '/servicesN.json')

    op_lines=[]
    for i in ret.items:
        port=""
        spec = i.spec.to_dict()

        ext_ips=spec['external_i_ps']

        # Needs checking, is it this field or load_balancer_ip ??
        if not ext_ips:
            ext_ips='Pending'

        if spec and 'ports' in spec and spec['ports'] and 'node_port' in spec['ports'][0]:
            port0=spec['ports'][0]
            if 'node_port' in port0 and port0['node_port'] is not None:
                port=f" {port0['port']}:{port0['node_port']}"
            else:
                port=f" {port0['port']}"
            port += f"/{port0['protocol']}"

        cluster_ip=spec['cluster_ip']
        if not cluster_ip:
            cluster_ip=''

        #policy=""
        age, age_hms = get_age(i)

        ns_info=''
        if p_namespace == 'all':
            ns_info=f'[{i.metadata.namespace:{NS_FMT}}] '

        #svc_info = f'{cluster_ip:14s} {svc_type:12s} {ext_ips:15s} {port:14s}{policy:8s} {age_hms}'
        svc_info = f'{cluster_ip:14s} {spec["type"]:12s} {ext_ips:15s} {port:14s} {age_hms}'
        line = f'  {ns_info} {i.metadata.name:{NAME_FMT}} {svc_info}\n'
        op_lines.append({'age': age, 'line': line})

    return res_type + sort_lines_by_age(op_lines)

def print_jobs(p_namespace='all'):
    ''' print resource info '''
    print(sprint_jobs(p_namespace))

def sprint_jobs(p_namespace='all'):
    ''' build single-line representing resource info '''
    #res_type =  'job/' if SHOW_TYPES else ''
    res_type =  'jobs:' if SHOW_TYPES else ''

    if p_namespace == 'all':
        ret = batchv1.list_job_for_all_namespaces(watch=False)
    else:
        ret = batchv1.list_namespaced_job(watch=False, namespace=p_namespace)
    if len(ret.items) == 0:
        return ''
    write_json_items(ret.items, TMP_DIR + '/jobsN.json')

    op_lines=[]
    for i in ret.items:
        age, age_hms = get_age(i)

        ns_info=''
        if p_namespace == 'all':
            ns_info=f'[{i.metadata.namespace:{NS_FMT}}] '

        line = f"  {ns_info} {i.metadata.name:{NAME_FMT}} {age_hms}\n"
        op_lines.append({'age': age, 'line': line})

    return res_type + sort_lines_by_age(op_lines)

def print_cron_jobs(p_namespace='all'):
    ''' print resource info '''
    print(sprint_cron_jobs(p_namespace))

def sprint_cron_jobs(p_namespace='all'):
    ''' build single-line representing resource info '''
    #res_type =  'cronjob/' if SHOW_TYPES else ''
    res_type =  'cronjobs:' if SHOW_TYPES else ''

    if p_namespace == 'all':
        ret = batchv1beta1.list_cron_job_for_all_namespaces(watch=False)
    else:
        ret = batchv1beta1.list_namespaced_cron_job(watch=False, namespace=p_namespace)
    if len(ret.items) == 0:
        return ''
    write_json_items(ret.items, TMP_DIR + '/cronjobsN.json')

    op_lines=[]
    for i in ret.items:
        age, age_hms = get_age(i)
        ns_info=''
        if p_namespace == 'all':
            ns_info=f'[{i.metadata.namespace:{NS_FMT}}] '

        line = f"{ns_info} {i.metadata.name:{NAME_FMT}} {age_hms}\n"
        op_lines.append({'age': age, 'line': line})

    return res_type + sort_lines_by_age(op_lines)

def test_methods():
    ''' test print and sprintf methods '''

    print("======== Listing nodes with their IPs:")
    print_nodes()

    print("======== [all namespaces] Listing pods with their IPs:")
    print_pods()
    print("---- [namespace='default'] Listing pods with their IPs:")
    print_pods(p_namespace='default')

    print("======== [all namespaces] Listing deployments:")
    print_deployments()
    print("---- [namespace='default'] Listing deployments:")
    print_deployments(p_namespace='default')

    print("======== [all namespaces] Listing daemon_sets:")
    print_daemon_sets()
    print("---- [namespace='default'] Listing daemon_sets:")
    print_daemon_sets(p_namespace='default')

    print("======== [all namespaces] Listing stateful_sets:")
    print_stateful_sets()
    print("---- [namespace='default'] Listing stateful_sets:")
    print_stateful_sets(p_namespace='default')

    print("======== [all namespaces] Listing replica_sets:")
    print_replica_sets()
    print("---- [namespace='default'] Listing replica_sets:")
    print_replica_sets(p_namespace='default')

    print("======== [all namespaces] Listing stateful_sets:")
    print_stateful_sets()
    print("---- [namespace='default'] Listing stateful_sets:")
    print_stateful_sets(p_namespace='default')

    print("======== [all namespaces] Listing services:")
    print_services()
    print("---- [namespace='default'] Listing services:")
    print_services(p_namespace='default')

    print("======== [all namespaces] Listing jobs:")
    print_jobs()
    print("---- [namespace='default'] Listing jobs:")
    print_jobs(p_namespace='default')

    print("======== [all namespaces] Listing cron_jobs:")
    print_cron_jobs()
    print("---- [namespace='default'] Listing cron_jobs:")
    print_cron_jobs(p_namespace='default')

def namespace_exists(p_namespace):
    ''' check if namespace exists - or True if 'all' specified '''
    if p_namespace == "all":
        return True

    ret = corev1.list_namespace(watch=False)
    for i in ret.items:
        if i.metadata.name == p_namespace:
            return True
    return False

def build_context_namespace_resources_info(p_context, p_namespace, p_resources):
    ''' convenience: build up context status line '''
    pr_context=f'{ bold_white("Context:") } { bold_green(p_context) }'
    #pr_resources=f'{ bold_white("Resources:") } { bold_green(p_resources) }'
    pr_resources=f'{ bold_white("Resources:") } { bold_green( ",".join(p_resources)) }'
    if namespace_exists(p_namespace):
        pr_namespace=f'{ bold_white("Namespace:") } { bold_green(p_namespace) }'
    else:
        pr_namespace=f'{ bold_white("Namespace:") } { bold_red(p_namespace) }'

    return f'{ pr_context } / { pr_namespace } / { pr_resources }'

def cls():
    ''' clear screen '''
    sys.stdout.write('\033[H\033[J')

def main_setup(p_resources, p_namespace):
    ''' Normalize resources/namespace argument values '''
    final_resources=[]
    for reslist in p_resources:
        if "," in reslist:
            resource_list = reslist.split(",")
            final_resources.extend(resource_list)
        else:
            resource_list = reslist
            final_resources.append(resource_list)

    ret_resources=final_resources
    ret_namespace=p_namespace

    if p_namespace is None:
        ret_namespace=DEFAULT_NAMESPACE
    if p_namespace == "-":
        ret_namespace="all"

    if len(ret_resources) == 0:
        ret_resources = default_resources

    return (ret_resources, ret_namespace)

def main_loop():
    ''' Main execution loop '''
    full_context = build_context_namespace_resources_info(context, namespace, resources)
    print(f'full_context={full_context}\n')

    global nodes

    last_output=''
    while True:
        output=''

        full_context = build_context_namespace_resources_info(context, namespace, resources)
        output += full_context + '\n'

        nodes = get_nodes()

        for resource in resources:
            output += sprint_resource(resource)

        if output != last_output:
            cls()
            print(output)
            last_output = output

        time.sleep(0.5)     # Sleep for 500 milliseconds

def sprint_all_resources(resource):
    ''' Build up output for 'all' resource types '''
    output = ''
    if resource.find("nall") == 0:
        output=sprint_nodes()
    output+=sprint_services(namespace)
    output+=sprint_deployments(namespace)
    output+=sprint_replica_sets(namespace)
    output+=sprint_stateful_sets(namespace)
    output+=sprint_pods(namespace)
    output+=sprint_jobs(namespace)
    output+=sprint_cron_jobs(namespace)
    output+=sprint_pvs(namespace)
    output+=sprint_pvcs(namespace)
    return output

def sprint_resource(resource):
    ''' Build up output for 'resource' type '''
    retstr = None

    if resource.find("no") == 0:
        retstr = sprint_nodes()
    if resource.find("all") == 0 or resource.find("nall") == 0:
        retstr = sprint_all_resources(resource)
    if resource.find("svc") == 0 or resource.find("service") == 0:
        retstr = sprint_services(namespace)
    if resource.find("dep") == 0:
        retstr = sprint_deployments(namespace)
    if resource.find("ds") == 0 or resource.find("dset") == 0 or resource.find("daemonset") == 0:
        retstr = sprint_daemon_sets(namespace)
    if resource.find("rs") == 0 or resource.find("replicaset") == 0:
        retstr = sprint_replica_sets(namespace)
    if resource.find("ss") == 0 or resource.find("sts") == 0:
        retstr = sprint_stateful_sets(namespace)
    if resource.find("po") == 0:
        retstr = sprint_pods(namespace)
    if resource.find("job") == 0:
        retstr = sprint_jobs(namespace)
    if resource.find("cj") == 0 or resource.find("cron") == 0:
        retstr = sprint_cron_jobs(namespace)
    if resource.find("pvc") == 0:
        retstr = sprint_pvcs(namespace)
    #if resource.find("pv") == 0:
    if resource == "pv":
        retstr = sprint_pvs(namespace)

    if retstr is None:
        die(f"No match for resource type '{resource}'")

    return retstr

## -- Args: ----------------------------------------------------

def parse_args():
    ''' Parse command-line arguments '''
    arg_idx=1
    args_namespace=None
    args_resources=[]
    args_show_types=True
    args_verbose=False

    while arg_idx <= (len(sys.argv)-1):
        arg=sys.argv[arg_idx]
        arg_idx+=1
        if arg == "-st":
            args_show_types=True
            continue
        if arg == "-show-types":
            args_show_types=True
            continue
        if arg == "-nst":
            args_show_types=False
            continue
        if arg == "-no-show-types":
            args_show_types=False
            continue

        if arg == "-v":
            args_verbose=True
            continue

        if arg == "-test":
            test_methods()
            sys.exit(0)

        if arg == "-slow":
            # Slow changing resources:
            args_resources = [ 'node', 'svc', 'deploy', 'ds', 'rs', 'ss' ]
            continue

        if arg == "-A":
            args_namespace="-"
            continue

        if arg == "-n":
            args_namespace=sys.argv[arg_idx]
            arg_idx+=1
            continue

        if arg == "-r":
            args_resources.append(sys.argv[arg_idx])
            arg_idx+=1
            continue

        args_resources.append( arg )

    return (args_namespace, args_resources, args_show_types, args_verbose)

## -- Main: ----------------------------------------------------

(namespace, resources, SHOW_TYPES, VERBOSE)=parse_args()

nodes = get_nodes()

if __name__ == "__main__":
    (resources, namespace) = main_setup(resources, namespace)
    main_loop()
