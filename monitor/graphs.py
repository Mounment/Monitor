#!/usr/bin/env python
# -*- coding: utf-8 -*-
# __author__= 'luhj'
from monitor import models

class GraphGenerator2(object):

    def __init__(self,request,redis_obj):
        self.request = request
        self.redis = redis_obj
        self.host_id = self.request.GET.get('host_id')
        self.time_range = self.request.GET.get('time_range')


    def get_host_generator(self):
        '''生成主机关联的所有service的图形'''
        host_obj = models.Host.objects.get(id=self.host_id)
        service_data_dic = {}
        template_list = list(host_obj.templates.select_related())
        for g in host_obj.host_groups.select_related():
            template_list.extend(g.templates.select_related())
        template_list = set(template_list)
        for template in template_list:
            for service in template.services.select_related():
                service_data_dic[service.id] = {
                    'name':service.name,
                    'index_data':{},
                    'has_sub_server':service.has_sub_service,
                    'raw_data':[],
                    'items':[item.key for item in service.items.select_related()]
                }

        print(service_data_dic)
        for service_id,val_dic in service_data_dic.items():
            service_redis_key = 'StatusData_%s_%s_%s'%(self.host_id,val_dic['name'],self.time_range)
            print('service_redis_key', service_redis_key)
            service_raw_data = self.redis.lrange(service_redis_key,0,-1)
            service_raw_data = [item.decode() for item in service_raw_data]
            service_data_dic[service_id]['raw_data'] = service_raw_data
        return service_data_dic

