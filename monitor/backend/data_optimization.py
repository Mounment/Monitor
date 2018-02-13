#!/usr/bin/env python
# -*- coding: utf-8 -*-
# __author__= 'luhj'

from django.conf import settings
import json,time,copy

class DataStore(object):
    '''把客户端返回的数据存到客户端的redis中'''
    def __init__(self,client_id,service_name,data,redis_obj):
        self.client_id = client_id
        self.service_name = service_name
        self.data = data
        self.redis_conn_obj = redis_obj
        self.process_and_save()

    def get_average(self, data_set):
        if len(data_set) > 0:
            return round(sum(data_set) / len(data_set), 2)
        else:
            return 0

    def get_max(self, data_set):
        if len(data_set) > 0:
            return max(data_set)
        else:
            return 0

    def get_min(self, data_set):
        if len(data_set) > 0:
            return min(data_set)
        else:
            return 0

    def get_mid(self, data_set):
        data_set.sort()
        if len(data_set) > 0:
            return data_set[int(len(data_set) / 2)]
        else:
            return 0

    def process_and_save(self):
        if self.data['status'] == 0:
            for key,data_series_val in settings.STATUS_DATA_OPTIMIZATION.items():
                data_series_optimize,max_data_point = data_series_val # 'latest':[0,600]
                data_series_key_in_redis = 'StatusData_%s_%s_%s'%(self.client_id,
                                                                  self.service_name,key)
                last_point_from_redis = self.redis_conn_obj.lrange(data_series_key_in_redis,-1,-1)
                if not last_point_from_redis:
                    '''第一次汇报为空,初始化列表'''
                    self.redis_conn_obj.rpush(data_series_key_in_redis,json.dumps([None,time.time()]))
                if data_series_optimize == 0: #表示不需要优化
                    self.redis_conn_obj.rpush(data_series_key_in_redis,json.dumps([self.data,time.time()]))
                else:
                    last_point_data,last_point_save_time = json.loads(self.redis_conn_obj.lrange(data_series_key_in_redis,-1,-1)[0].decode())
                    if time.time() - last_point_save_time >= data_series_optimize:
                        lastest_data_key_in_redis = 'StatusData_%s_%s_latest'%(self.client_id,self.service_name)
                        print("calulating data for key:\033[31;1m%s\033[0m" % data_series_key_in_redis)

                        #获取需要优化的数据
                        data_set = self.get_data_slice(lastest_data_key_in_redis,data_series_optimize)
                        if len(data_set) > 0:
                            #优化数据点
                            optimized_data = self.get_optimized_data(data_series_key_in_redis,data_set)
                            if optimized_data:
                                #保存到redis中
                                self.save_optimized_data(data_series_key_in_redis,optimized_data)
                #如果超过了最大的点,删除最旧的一个
                if self.redis_conn_obj.llen(data_series_key_in_redis) >= max_data_point:
                    self.redis_conn_obj.lpop(data_series_key_in_redis)
        else:
            print("report data is invalid::", self.data)
            raise ValueError



    def get_data_slice(self,lastest_data_key,optimization_interval):
        all_real_data = self.redis_conn_obj.lrange(lastest_data_key,-1,-1)
        data_set = [] #存放符合条件的数据
        for item in all_real_data:
            data = json.loads(item.decode())
            if len(data) == 2:
                service_data,last_save_time = data
                #将没有超时条件的点存放在dataset中
                if time.time() - last_save_time <= optimization_interval:
                    data_set.append(data)
                else:
                    pass
        return data_set


    def get_optimized_data(self,data_set_key,raw_service_data):
        service_data_keys = raw_service_data[0][0].keys() #['iowait','idle','....']
        first_service_data_point = raw_service_data[0][0]
        optimized_dic = {}
        '''表示是cpu,内存,load的数据不包括网卡'''
        if 'data' not in service_data_keys:
            for key in service_data_keys:
                optimized_dic[key] = []
            tmp_data_dic = copy.deepcopy(optimized_dic)

            for service_data_item,last_save_time in raw_service_data:
                for service_index,v in service_data_item.items():
                    try:
                        tmp_data_dic[service_index].append(round(float(v),2))
                    except ValueError as e:
                        pass

            for service_k,v_list in tmp_data_dic.items():
                #对内部的值求平均,最大,最小,中位数
                avg_res = self.get_average(v_list)
                max_res = self.get_max(v_list)
                min_res = self.get_min(v_list)
                mid_res = self.get_mid(v_list)
                optimized_dic[service_k] = [avg_res,max_res,min_res,mid_res]
        else:
            for service_item_key,v_dic in first_service_data_point['data'].items():
                optimized_dic[service_item_key] = {}
                #v_dic = {t_in:333,t_out:3344}
                for k2,v2 in v_dic.items():
                    #{etho0:{t_in:[],t_out:[]}}
                    optimized_dic[service_item_key][k2] = []

            tmp_data_dic = copy.deepcopy(optimized_dic)
            if tmp_data_dic:
                for service_data_item,last_save_time in raw_service_data:
                    for service_index,val_dic in service_data_item['data'].items():
                        for service_item_sub_key,val in val_dic.items():
                            tmp_data_dic[service_index][service_item_sub_key].append(round(float(val),2))

                for service_k,v_dic in tmp_data_dic.items():
                    for service_sub_k,v_list in v_dic.items():
                        avg_res = self.get_average(v_list)
                        max_res = self.get_max(v_list)
                        min_res = self.get_min(v_list)
                        mid_res = self.get_mid(v_list)
                        optimized_dic[service_k][service_sub_k] = [avg_res,max_res,min_res,mid_res]

            else:
                print("\033[41;1mMust be sth wrong with client report data\033[0m")
        print("optimized empty dic:", optimized_dic)
        return optimized_dic



    def save_optimized_data(self,data_series_key_in_redis,optimized_data):
        self.redis_conn_obj.rpush(data_series_key_in_redis,json.dumps([optimized_data,time.time()]))
