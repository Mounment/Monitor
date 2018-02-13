#!/usr/bin/env python
# -*- coding: utf-8 -*-
# __author__= 'luhj'
from django.shortcuts import render,HttpResponse
from monitor import serializer
from monitor.serializer import  ClientHandler,get_service_trigger
from monitor.backend import redis_conn
from monitor.backend import data_processing
from django.conf import settings
from monitor import models
from monitor.backend import data_optimization
import json
from monitor import graphs
from django.views.decorators.csrf import csrf_exempt


REDIS_OBJ = redis_conn.redis_conn(settings)

def client_config(request,client_id):
    config_obj = ClientHandler(client_id)
    config = config_obj.fetch_configs()
    if config:
        return HttpResponse(json.dumps(config))

@csrf_exempt
def service_report(request):
    if request.method == 'POST':
        try:
            print('host=%s, service=%s' % (request.POST.get('client_id'), request.POST.get('service_name')))
            data = json.loads(request.POST['data'])
            client_id = request.POST.get('client_id')
            service_name = request.POST.get('service_name')
            data_saving_obj = data_optimization.DataStore(client_id,service_name,data,REDIS_OBJ)
            host_obj = models.Host.objects.get(id=client_id)#同时出发trigger检测
            service_trigger = get_service_trigger(host_obj)
            trigger_handler = data_processing.DataHandler(settings,connect_redis=False)
            for trigger in service_trigger:
                trigger_handler.load_service_data_calulating(host_obj,trigger,REDIS_OBJ)
        except IndexError as e:
            print('----->err:', e)
    return HttpResponse(json.dumps("---report success---"))




def hosts_status(request):
    '''主机状态'''
    hosts_data_serializer = serializer.StatusSerializer(request,REDIS_OBJ)
    hosts_data = hosts_data_serializer.by_hosts()
    return HttpResponse(json.dumps(hosts_data))

def hostgroups_status(request):
    group_serializer = serializer.GroupSerializer(request,REDIS_OBJ)
    group_serializer.get_all_group_status()
    return HttpResponse('ok')

def graphs_generator(request):
    graphs_generator = graphs.GraphGenerator2(request,REDIS_OBJ)
    graphs_data = graphs_generator.get_host_generator()
    return HttpResponse(json.dumps(graphs_data))



