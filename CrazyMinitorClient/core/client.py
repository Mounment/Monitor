#!/usr/bin/env python
# -*- coding: utf-8 -*-
# __author__= 'luhj'


import json
from conf import settings
import urllib
import urllib2
import time
import threading
from plugins import plugin_api

class ClientHandler(object):
    def __init__(self):
        self.monitored_services = {}

    def load_last_configs(self):
        request_type = settings.configs['urls']['get_configs'][1]
        url = '%s/%s'%(settings.configs['urls']['get_configs'][0],settings.configs['HostID'])
        lastest_configs = self.url_request(request_type,url)
        lastest_configs = json.loads(lastest_configs)
        self.monitored_services.update(lastest_configs)

    def url_request(self,action,url,**extra_data):
        abs_url = 'http://%s:%s/%s'%(settings.configs['Server'],
                                     settings.configs['ServerPort'],
                                     url)
        if action in {'get','GET'}:
            try:
                req = urllib2.Request(abs_url)
                req_data = urllib2.urlopen(req,timeout=settings.configs['RequireTimeOut'])
                callback = req_data.read()
                return callback
            except urllib2.URLError as e:
                exit("\033[31;1m%s\033[0m" % e)
        elif action in {'post','POST'}:
            try:
                data_encode = urllib.urlencode(extra_data['params'])
                req = urllib2.Request(url=abs_url,data=data_encode)
                req_data = urllib2.urlopen(req,timeout=settings.configs['RequireTimeOut'])
                callback = req_data.read()
                callback = json.loads(callback)
                return callback
            except Exception as e:
                print('---exec', e)
                exit("\033[31;1m%s\033[0m" % e)

    def invoke_plugin(self,service_name,val):
        plugin_name = val[0]
        if hasattr(plugin_api,plugin_name):
            func = getattr(plugin_api,plugin_name)
            plugin_callback = func()
            report_data ={
                'client_id':settings.configs['HostID'],
                'service_name':service_name,
                'data':json.dumps(plugin_callback)
            }
            request_action = settings.configs['urls']['service_report'][1]
            request_url = settings.configs['urls']['service_report'][0]
            self.url_request(request_action,request_url,params=report_data)
        else:
            print("\033[31;1m找不到 [%s] 服务对应的插件名称 [%s] \033[0m"% (service_name,plugin_name ))
        print('--plugin:', val)


    def forever_run(self):
        exit_flag = False
        config_last_update_time = 0
        while not exit_flag:
            if time.time() - config_last_update_time > settings.configs['ConfigUpdateInterval']:
                self.load_last_configs()
                print("Loaded latest config:", self.monitored_services)
                config_last_update_time = time.time()
            for service_name,val in self.monitored_services['services'].items():
                if len(val) == 2:
                    self.monitored_services['services'][service_name].append(0)
                monitor_interval = val[1]
                last_invoke_time = val[2]
                if time.time() - last_invoke_time > monitor_interval:
                    print(last_invoke_time, time.time())
                    self.monitored_services['services'][service_name][2] = time.time()
                    t = threading.Thread(target=self.invoke_plugin,args=(service_name,val))
                    t.start()
                    print("准备监控的主机 [%s]" % service_name)
                else:
                    print("准备监控的主机 [%s] 间隔 [%s] /秒" % (service_name,
                                                                  monitor_interval - (time.time() - last_invoke_time)))
