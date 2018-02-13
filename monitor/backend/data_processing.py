#!/usr/bin/env python
# -*- coding: utf-8 -*-
# __author__= 'luhj'
import time,json,pickle
from django.conf import settings
from monitor import models
from monitor.backend import redis_conn
import operator
class DataHandler(object):

    def __init__(self,django_settings,connect_redis=True):
        self.django_settings = settings
        self.poll_interval = 3 #每3秒进行一次全局轮询
        self.config_update_interval = 120 #每120秒加载一次数据库的配置
        self.config_last_loading_time = time.time()
        self.global_monitor_dic = {}
        self.exit_flag = False
        if connect_redis:
            self.redis = redis_conn.redis_conn(settings)

    def looping(self):
        '''检测所有主机所需要的服务数据是否按时汇报'''

        self.update_or_load_configs()
        count = 0
        while not self.exit_flag:
            print("looping %s".center(50, '-') % count)
            count += 1
            #如果大于轮询的时间,从数据库再取一次数据,重新获取,global_monitor_dic
            if time.time() - self.config_last_loading_time >= self.config_update_interval:
                print("\033[41;1mneed update configs ...\033[0m")
                self.update_or_load_configs()
                print("monitor dic", self.global_monitor_dic)
            if self.global_monitor_dic:
                for h,config_dic in self.global_monitor_dic.items():
                    '''
                    config_dic
                            {'services'{'cpu':[cpu_obj,0],
                                         'mem':[mem_obj,0]
                                         },
                              'trigger':{t1:t1_obj,}
                    '''
                    print('handling host:\033[32;1m%s\033[0m' % h)
                    #循环所有要监控的服务
                    for service_id,val in config_dic['services'].items():
                        service_obj,last_monitor_time = val
                        if time.time() - last_monitor_time >= service_obj.interval:
                            #如果大于轮询时间
                            print("\033[33;1mserivce [%s] has reached the monitor interval...\033[0m" % service_obj.name)
                            #将时间更新'cpu':[cpu_obj,0],此列表的第二个值
                            self.global_monitor_dic[h]['services'][service_obj.id][1] = time.time()
                            self.data_point_validation(h,service_obj) #检测此服务最近汇报的数据
                        else:
                            next_monitor_time = time.time()-last_monitor_time-service_obj.interval
                            print("service [%s] next monitor time is %s" % (service_obj.name, next_monitor_time))

                    if time.time() - self.global_monitor_dic[h]['status_last_check'] > 10:
                        trigger_redis_key = 'host_%s_trigger*'%h.id
                        trigger_keys = self.redis.keys(trigger_redis_key)
                        if len(trigger_keys) == 0:
                            h.status = 1
                            h.save()
            time.sleep(self.poll_interval)


    def data_point_validation(self,host_obj,service_obj):
        '''监控点检测'''
        service_redis_key = 'StatusData_%s_%s_latest'%(host_obj.id,service_obj.name)
        latest_data_point = self.redis.lrange(service_redis_key,-1,-1)
        if latest_data_point:
            latest_data_point = json.loads(latest_data_point[0].decode())
            print("\033[41;1mlatest data point\033[0m %s" % latest_data_point)
            latest_service_data,last_report_time = latest_data_point
            #最大超时时间
            monitor_interval = service_obj.interval + self.django_settings.REPORT_LATE_TOLERANCE_TIME
            if time.time() - last_report_time > monitor_interval:
                no_data_secs = time.time() - last_report_time
                msg = '''Some thing must be wrong with client [%s] , because haven't receive data of service [%s] \
                               for [%s]s (interval is [%s])\033[0m''' % (host_obj.ip_addr, service_obj.name, no_data_secs, monitor_interval)
                #监控主机存活是默认的，不需要配置trigger就可以监控
                self.trigger_notifier(host_obj=host_obj,trigger_id=None,positive_expressions=None,
                                      msg=msg)
                print("\033[41;1m%s\033[0m" % msg)
                #监控主机是否存活
                if service_obj.name == 'uptime':
                    host_obj.status = 3 #unreachable
                    host_obj.save()
                else:
                    host_obj.status = 5 #problem
                    host_obj.save()
        #没有数据
        else:
            print("\033[41;1m no data for serivce [%s] host[%s] at all..\033[0m" % (service_obj.name, host_obj.name))
            msg = '''no data for serivce [%s] host[%s] at all..''' % (service_obj.name, host_obj.name)
            self.trigger_notifier(host_obj=host_obj,trigger_id=None,positive_expressions=None,msg=msg)
            host_obj.status = 5  # problem
            host_obj.save()


    def update_or_load_configs(self):
        '''生成全局监控的dic'''
        all_enable_hosts = models.Host.objects.all()
        for h in all_enable_hosts:
            if h not in self.global_monitor_dic:
                #新主机
                self.global_monitor_dic[h] = {'services':{},'triggers':{}}
                '''
                格式:global_monitor_dic ={
                    'h1':{'services'{'cpu':[cpu_obj,0],
                                     'mem':[mem_obj,0]
                                     },
                          'trigger':{t1:t1_obj,}
                        }
                '''
            service_list = []
            trigger_list = []
            for group in h.host_groups.select_related():
                for template in group.templates.select_related():
                    #通过主机组找到模板,通过模板找到service和trigger放到对应的列表
                    service_list.extend(template.services.select_related())
                    trigger_list.extend(template.triggers.select_related())
                for service in service_list:
                    if service.id not in self.global_monitor_dic[h]['services']:
                        #拼接service字典,第一次值初始化为0
                        self.global_monitor_dic[h]['services'][service.id]=[service,0]
                    else:
                        self.global_monitor_dic[h]['services'][service.id][0] = service

                for trigger in trigger_list:
                    self.global_monitor_dic[h]['triggers'][trigger.id] = trigger

            for template in h.templates.select_related():
                #通过主机找出其对应的service和trigger
                service_list.extend(template.services.select_related())
                trigger_list.extend(template.triggers.select_related())
            for service in service_list:
                if service.id not in self.global_monitor_dic[h]['services']:
                    self.global_monitor_dic[h]['services'][service.id]=[service,0]
                else:
                    self.global_monitor_dic[h]['services'][service.id][0] = service
            for trigger in trigger_list:
                self.global_monitor_dic[h]['triggers'][trigger.id] = trigger

            #通过这个时间来确定是否需要更新主机状态
            self.global_monitor_dic[h].setdefault('status_last_check',time.time())
        self.config_last_loading_time = time.time()
        return True


    def load_service_data_calulating(self,host_obj,trigger_obj,redis_obj):
        self.redis = redis_obj
        calc_sub_res_list = [] #先把每个expression的结果算出来放到这个列表里,最后统一计算这个列表
        positive_expressions = [] #存放条件为true的表达式
        expression_res_string = '' #用于拼接表达式
        for expression in trigger_obj.triggerexpression_set.select_related().order_by('id'):
            print(expression, expression.logic_type)
            expression_process_obj = ExpressionProcess(self,host_obj,expression) #处理单条表达式实例
            single_expression_res = expression_process_obj.process() #单条表达式的处理方法,返回dic,{'calc_res':True}
            if single_expression_res:
                calc_sub_res_list.append(single_expression_res) #把单条表达式的值放入到结果列表
                if single_expression_res['expression_obj'].logic_type: #不是最后一个条件
                    expression_res_string += str(single_expression_res['calc_res']) + ' ' + \
                        single_expression_res['expression_obj'].logic_type + ' '
                else:
                    expression_res_string += str(single_expression_res['calc_res'])

                #找出所有为true的表达式,报警的时候由trigger触发
                if single_expression_res['calc_res'] == True:
                    #把对象转换为字符,否则不能存放到redis中
                    single_expression_res['expression_obj'] = single_expression_res['expression_obj'].id
                    positive_expressions.append(single_expression_res)
        print("whole trigger res:", trigger_obj.name,expression_res_string)

        if expression_res_string:
            #计算整个表达式的值
            trigger_res = eval(expression_res_string)
            print("whole trigger res:", trigger_res)
            if trigger_res: #结果值为true就触发报警
                print("##############trigger alert:", trigger_obj.severity, trigger_res)
                #触发报警
                self.trigger_notifier(host_obj,trigger_obj.id,positive_expressions,msg=trigger_obj.name)


    def trigger_notifier(self,host_obj,trigger_id,positive_expressions,redis_obj=None,msg=None):
        #避免redis重复调用
        if redis_obj:
            self.redis = redis_obj

        msg_dic = {'host_id':host_obj.id,
                   'trigger_id':trigger_id,
                   'positive_expressions':positive_expressions, #对象
                   'msg':msg,
                   'time':time.strftime('%Y-%m-%d %H:%M:%S',time.localtime()),
                   'start_time':time.time(),
                   'duration':None
        }
        #将msg_dic推送给redis队列
        self.redis.publish(self.django_settings.TRIGGER_CHAN,pickle.dumps(msg_dic))

        #根据trigger计算故障的时间
        trigger_redis_key = 'host_%s_trigger_%s'%(host_obj.id,trigger_id)
        old_trigger_data = self.redis.get(trigger_redis_key)
        if old_trigger_data:
            old_trigger_data = old_trigger_data.decode()
            trigger_startime = json.loads(old_trigger_data)['start_time']
            msg_dic['start_time'] = trigger_startime
            msg_dic['duration'] = round(time.time()-trigger_startime)

        self.redis.set(trigger_redis_key,json.dumps(msg_dic),300)

class ExpressionProcess(object):
    '''计算单条表达式结果'''
    def __init__(self,main_ins,host_obj,expression_obj,specified_item=None):
        self.host_obj=host_obj
        self.expression_obj=expression_obj
        self.main_ins = main_ins
        self.service_redis_key = 'StatusData_%s_%s_latest'%(host_obj.id,expression_obj.service.name)
        self.time_range = self.expression_obj.data_calc_args.split(',')[0] #取出在redis要存放多长时间
        print("\033[31;1m------>%s\033[0m" % self.service_redis_key)

    def load_data_from_redis(self):
        time_in_sec = 60 * int(self.time_range) #将数据转换成秒
        #获取时间点,多取一个后面会自动忽略
        approximate_data_points = (time_in_sec + 60) / self.expression_obj.service.interval
        print("approximate dataset nums:", approximate_data_points, time_in_sec)
        #从redis中取出所有的点
        data_range_raw = self.main_ins.redis.lrange(self.service_redis_key,-int(approximate_data_points),-1)
        approximate_data_range = [json.loads(i.decode()) for i in data_range_raw]
        data_range = [] #存放精确的数据
        for point in approximate_data_range:
            val,saving_time = point
            #数据有效
            if time.time() - saving_time > time_in_sec:
                data_range.append(point)

        print(data_range)
        return data_range

    def process(self):
        '''
        处理单条表达式的结果
        1.从redis中获取有效的列表
        2.根据函数找到各个值组成dic返回
        '''

        data_list = self.load_data_from_redis()
        data_calc_func = getattr(self,'get_%s'%self.expression_obj.data_calc_func)
        single_expression_calc_res = data_calc_func(data_list)
        print("---res of single_expression_calc_res ", single_expression_calc_res)
        if single_expression_calc_res:
            res_dic={
                'calc_res':single_expression_calc_res[0],
                'calc_res_val':single_expression_calc_res[1],
                'expression_obj':self.expression_obj,
                'service_item':single_expression_calc_res[2]
            }
            print("\033[41;1msingle_expression_calc_res:%s\033[0m" % single_expression_calc_res)
            return res_dic
        else:
            return False



    def get_avg(self,data_list):
        clean_data_list = [] #存放清洗之后的数据
        clean_data_dic = {}
        for point in data_list:
            val,save_time = point
            if val:
                if 'data' not in val:
                    #将符合条件的监控指标全部过滤出来
                    clean_data_list.append(val[self.expression_obj.service_index.key])
                else:
                    #网卡过滤
                    for k,v in val['data'].items():
                        if k not in clean_data_dic:
                            clean_data_list[k] = []
                        clean_data_dic[k].append(v[self.expression_obj.service_index.key])

        if clean_data_list:
            clean_data_list = [float(i) for i in clean_data_list]
            avg_res = sum(clean_data_list)/len(clean_data_list)
            return [self.judge(avg_res),avg_res,None]

        elif clean_data_dic:
            for k,v in clean_data_dic.items():
                clean_v_list = [float(i) for i in v]
                avg_res = 0 if sum(clean_v_list) == 0 else sum(clean_v_list) / len(clean_v_list)
                print("\033[46;1m-%s---avg res:%s\033[0m" % (k, avg_res))
                #监控了特定的指标,比如只要eth0
                if self.expression_obj.specified_index_key:
                    if k == self.expression_obj.specified_index_key:
                        print("test res [%s] [%s] [%s]=%s") % (avg_res,
                                                               self.expression_obj.operator_type,
                                                               self.expression_obj.threshold,
                                                               self.judge(avg_res),
                                                               )
                        calc_res = self.judge(avg_res)
                        if calc_res:
                            return [calc_res,avg_res,None]
                #表示监控所有子项
                else:
                    calc_res = self.judge(avg_res)
                    if calc_res:
                        return [calc_res,avg_res,k]
                print('specified monitor key:', self.expression_obj.specified_index_key)
                print('clean data dic:', k, len(clean_v_list), clean_v_list)
            else:
                return [False,avg_res,k]

        else:
            return [False,None,None]


    def judge(self,calculated_val):
        '''判断是否是符合data_calc_func的结果,和阈值相比较'''
        calc_func = getattr(operator,self.expression_obj.operator_type)
        return calc_func(calculated_val,self.expression_obj.threshold)