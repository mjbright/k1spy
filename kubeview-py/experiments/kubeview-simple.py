#!/usr/bin/env python3

import os
import sys
import copy

import time
# For timestamp handling:
from datetime import datetime
import json

#from datetime import timezone

from kubernetes import client, config

NAME_FMT="32s"
INFO_FMT="60s"
NS_FMT="15s"

SHOW_TYPES=False
VERBOSE=False
nodes=[]
resources=[]
namespace='default'

DEFAULT_NAMESPACE='default'
DEBUG=0
DEBUG=1

## -- Funcs: ----------------------------------------------------------------------

def die(msg):
    ''' exit after printing bold-red error 'msg' text'''
    print(f"die: { bold_red(msg) }")
    sys.exit(1)



def get_deployments(p_namespace='all'):

    if p_namespace == 'all':
        ret = appsv1.list_deployment_for_all_namespaces(watch=False)
    else:
        ret = appsv1.list_namespaced_deployment(watch=False, namespace=p_namespace)

    if len(ret.items) == 0:
        return []

    #op_lines=[]
    ret_items = {}
    for i in ret.items:
        info       = get_replicas_info(i)
        image_info = get_image_info(i)
        age, age_hms = get_age(i)

        name = i.metadata.name
        if p_namespace == 'all':
            ns = i.metadata.namespace
        else:
            ns = namespace

        summary = f"  {i.metadata.name:{NAME_FMT}} {info:{INFO_FMT}} {age_hms} {image_info}\n"
        #ret_items = {f'{ns}/{name}': {'ns': ns, 'info': info, 'image_info': image_info, 'age': age, 'age_hms': age_hms, 'summary': summary} }
        ret_items[f'{ns}/{name}'] = {'info': info, 'image_info': image_info, 'age': age, 'age_hms': age_hms, 'summary': summary}
        #ret_items += {f'{ns}/{name}': {'info': info, 'image_info': image_info, 'age': age, 'age_hms': age_hms, 'summary': summary} }

        #op_lines.append({'age': age, 'line': line})

    #return res_type + sort_lines_by_age(op_lines)
    if DEBUG > 0: print(f'Number of deployments: {len(ret.items)}')
    return ret_items

def sprint_deployments(p_namespace='all'):
    ''' build single-line representing resource info '''
    #res_type =  'deployments:' if SHOW_TYPES else ''
    res_type =  ''

    if p_namespace == 'all':
        ret = appsv1.list_deployment_for_all_namespaces(watch=False)
    else:
        ret = appsv1.list_namespaced_deployment(watch=False, namespace=p_namespace)

    if len(ret.items) == 0:
        return ''

    # write_json_items(ret.items, TMP_DIR + '/deploysN.json')

    op_lines=[]
    for i in ret.items:
        info=get_replicas_info(i)
        image_info = get_image_info(i)
        age, age_hms = get_age(i)

        ns_info=''
        if p_namespace == 'all':
            ns_info=f'[{i.metadata.namespace:{NS_FMT}}] '

        line = f"  {ns_info} {i.metadata.name:{NAME_FMT}} {info:{INFO_FMT}} {age_hms} {image_info}\n"
        op_lines.append({'age': age, 'line': line})

    return res_type + sort_lines_by_age(op_lines)

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

def get_replicas_info(instance):
    ''' get info about pod replicas for controller instance '''
    spec_replicas=0
    spec_parallelism=-1

    if hasattr(instance.spec, 'replicas'):
        spec_replicas=instance.spec.replicas
    if hasattr(instance.spec, 'job_template'): # Jobs/CronJobs
        spec_replicas=instance.spec.job_template.spec.completions
        if spec_replicas == None:
            spec_replicas=1
        spec_parallelism=instance.spec.job_template.spec.parallelism
        if spec_parallelism == None:
            spec_parallelism=1

    stat_replicas=0
    if hasattr(instance.status, 'ready_replicas'):
        stat_replicas=instance.status.ready_replicas
    # This is for jobs/cronjobs - needs correcting
    # TODO: show number of job pods active / total jobs
    if hasattr(instance.status, 'active'):
        active = instance.status.active
        # print(f'type({active})={type(active)}\n')
        if active == None:
            stat_replicas=0
        elif isinstance(active,int):
            stat_replicas=active # isn't this an array of Object?
        else:
            print( stat_replicas )
            stat_replicas=len(active)
        #stat_replicas=instance.status.active # isn't this an array of Object?
        #if instance.status.active:

    jobs_extra=''
    if spec_parallelism>=0:
        jobs_extra=f'{spec_parallelism}/'

    if stat_replicas == spec_replicas:
        replicas_info=green(f'{stat_replicas}/{jobs_extra}{spec_replicas}')

    else:
        if stat_replicas is None:
            stat_replicas = 0
        replicas_info=yellow(f'{stat_replicas}/{jobs_extra}{spec_replicas}')

    return replicas_info

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

def get_image_info(instance):
    image_list=[]
    image_info=''

    if hasattr(instance.spec, 'template'):
        template_spec = instance.spec.template.spec
        image_list=[ container.image for container in template_spec.containers ]
    elif hasattr(instance.spec, 'job_template'):
        template_spec = instance.spec.job_template.spec.template.spec
        image_list=[ container.image for container in template_spec.containers ]
    else:
        image_list=[ container.image for container in instance.spec.containers ]

    if len(image_list) > 0:
        image_info = '[' + ','.join(image_list) + ']'

    #items[0].spec.template.spec.containers[].image
    #items[0].spec.containers[].image
    return image_info

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

def deepcompare_deployments(last, current):
    change = False
    # print("============ DEEP COMPARE ================")

    # print(f'LAST={last}')
    for ns_name in last.keys():
        # print(f'LAST[{ns_name}]')
        if ns_name not in current:
            print(f'Deleted deployment detected: {ns_name}')
            change = True
            break

    if change:
        # print(f'RET1: {change}')
        return True

    # print(f'CURRENT={current}')
    for ns_name in current.keys():
        # print(f'CURRENT[{ns_name}]')
        if ns_name not in last:
            print(f'New deployment detected: {ns_name}')
            change = True
            break
            #return True

        for key in current[ns_name].keys():
            if key == 'summary': continue
            if key == 'age':     continue
            if key == 'age_hms': continue

            if DEBUG > 1:
                print(f'DEBUG: current[{ns_name}]: { current[ns_name] }')
                print(f'DEBUG: last[{ns_name}]: { last[ns_name] }')
            current_val = current[ns_name][key]
            if DEBUG > 1:
                print(f'current_val={current_val}')
            last_val = last[ns_name][key]
            if DEBUG > 1:
                print(f'last_val={last_val}')

            if current_val != last_val:
                print(f'Deployment change detected: {ns_name} on "{key}": "{last_val}" != "{current_val}"')
                change = True
                break
                #return True

    if change:
        # print(f'RET2: {change}')
        return True

    #print(f'RET3: {change}')
    return False



## -- Main: -------------------------------------------------------

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

    ## -- Get context/namespace  information: -------------------------

    # {'context': {'cluster': 'kubernetes', 'namespace': 'k8scenario', 'user': 'kubernetes-admin'},
    #  'name': 'k8scenario'}
    contexts, active_context = config.list_kube_config_contexts()
    if 'namespace' in active_context['context']:
        DEFAULT_NAMESPACE=active_context['context']['namespace']

    #print(active_context)
    context=active_context['name']
    print(f'context={context} namespace={DEFAULT_NAMESPACE}')
else:
    print(f'No such kubeconfig file as "{KUBECONFIG}" - assuming in cluster')
    config.load_incluster_config()
    KUBECONFIG=None
    context=None

## -- Get API clients: --------------------------------------------

corev1 = client.CoreV1Api()
appsv1 = client.AppsV1Api()
batchv1 = client.BatchV1Api()
#batchv1beta1 = client.BatchV1beta1Api()
batchv1 = client.BatchV1Api()

## -- Main: : -----------------------------------------------------

last_op     = ''
last_deployments = {}
deployments      = {}

while True:
    changes = False

    deployments      = get_deployments(p_namespace='all')

    #if not changes:
    #    changes = deepcompare_deployments( last_deployments, deployments)
    changes = deepcompare_deployments( last_deployments, deployments)
    last_deployments = copy.deepcopy(deployments)

    if changes:
        op = sprint_deployments(p_namespace='all')
        #if op != last_op:
        print('--------')
        print(op)
    else:
        current_GMT_timestamp = datetime.utcnow()


        print(f'{ current_GMT_timestamp }: NO changes detected')

    time.sleep(1)

