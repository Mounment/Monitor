#!/usr/bin/env python
# -*- coding: utf-8 -*-
# __author__= 'luhj'
import pickle,time
from django.conf import settings
from django.core.mail import send_mail
from monitor import models
from monitor.backend import redis_conn


class TriggerHandler(object):

    def __init__(self,django_settings):
        self.django_settings = django_settings
        self.redis = redis_conn.redis_conn(self.django_settings)
        # 记录每个action的报警次数,格式{1:{2:{'counter':0','last_alert':None}}}
        #1是action_id,2是host_id
        self.alert_counters = {}

    def start_watching(self):
        '''开始监控每个触发器的是否有报警'''
        radio = self.redis.pubsub()
        radio.subscribe(self.django_settings.TRIGGER_CHAN)
        radio.parse_response()
        print("\033[43;1m************start listening new triggers**********\033[0m")
        self.trigger_count = 0
        while True:
            msg = radio.parse_response()
            self.trigger_consume(msg)

    def trigger_consume(self,msg):
        self.trigger_count += 1
        print("\033[41;1m************Got a trigger msg [%s]**********\033[0m" % self.trigger_count)
        trigger_msg = pickle.loads(msg[2])
        action = ActionHandler(trigger_msg,self.alert_counters)
        action.trigger_process()


class ActionHandler(object):
    '''将达到的报警条件进行分析,并根据action表来报警'''

    def __init__(self,trigger_data,alert_counter_dic):
        self.trigger_data = trigger_data
        self.alert_counter_dic=alert_counter_dic


    def record_log(self,action_obj,action_operation_obj,host_id,trigger_data):
        models.EventLog.objects.create(
            event_type = 0,
            host_id = host_id,
            trigger_id = trigger_data.get('trigger_id'),
            log = trigger_data
        )

    def action_sms(self, action_obj, action_operation_obj, host_id, trigger_data):
        print("going to send sms to ", action_operation_obj.notifiers.all())

    def action_email(self,action_obj,action_operation_obj,host_id,trigger_data):
        print("要发报警的数据:", self.alert_counter_dic[action_obj.id][host_id])
        print("action email:", action_operation_obj.action_type, action_operation_obj.notifiers, trigger_data)
        notifier_mail_list = [obj.user.email for obj in action_operation_obj.notifiers.all()]
        subject = '级别:%s -- 主机:%s -- 服务:%s' % (trigger_data.get('trigger_id'),
                                               trigger_data.get('host_id'),
                                               trigger_data.get('service_item'))
        send_mail(
            subject,action_operation_obj.msg_format,
            settings.DEFAULT_FROM_EMAIL,
            notifier_mail_list
        )


    def trigger_process(self):
        '''分析trigger并报警'''
        if self.trigger_data.get('trigger_id') == None:
            print(self.trigger_data)
            if self.trigger_data.get('msg'):
                print(self.trigger_data.get('msg'))
            else:
                print("\033[41;1mInvalid trigger data %s\033[0m" % self.trigger_data)
        # 开始报警逻辑
        else:
            print("\033[33;1m%s\033[0m" % self.trigger_data)
            trigger_id = self.trigger_data.get('trigger_id')
            host_id = self.trigger_data.get('host_id')
            trigger_obj = models.Trigger.objects.get(id=trigger_id)
            actions_set = trigger_obj.action_set.select_related()#找到trigger关联的action
            print("actions_set:", actions_set)
            matched_action_list = set() #存放匹配到的报警策略
            for action in actions_set:
                #找到所有主机和主机组的报警策略
                for hg in action.host_groups.select_related():
                    for h in hg.host_set.select_related():
                        if h.id == host_id:
                            #此条报警策略适用于该主机
                            matched_action_list.add(action)
                            if action.id not in self.alert_counter_dic:
                                #第一次触发,初始化一个dic
                                self.alert_counter_dic[action.id] = {}
                            print("action, ", id(action))
                            if h.id not in self.alert_counter_dic[action.id]:
                                #如果主机第一次触发报警,count为0
                                self.alert_counter_dic[action.id][h.id] = {'counter':0,'last_alert':time.time()}
                            else:
                                #表示要报警
                                if time.time() - self.alert_counter_dic[action.id][h.id]['last_alert'] >= action.interval:
                                    self.alert_counter_dic[action.id][h.id]['counter'] += 1
                                else:
                                    print('没达到alert interval时间,不报警',action.interval,
                                          time.time() - self.alert_counter_dic[action.id][h.id]['last_alert'])

                for host in action.hosts.select_related():
                    if host.id == host_id:#此action适用于该主机
                        matched_action_list.add(action)
                        #第一次被触发,初始化一个action,counter
                        if action.id not in self.alert_counter_dic:
                            self.alert_counter_dic[action.id] = {}
                        if h.id not in self.alert_counter_dic[action.id]:
                            #主机第一次触发报警
                            self.alert_counter_dic[action.id][h.id]={'counter':0,'last_alert':time.time()}
                        else:
                            if time.time() - self.alert_counter_dic[action.id][h.id]['last_alert'] >= action.interval:
                                self.alert_counter_dic[action.id][h.id]['counter'] += 1
                            else:
                                print('没达到alert interval时间,不报警', action.interval,
                                      time.time() - self.alert_counter_dic[action.id][h.id]['last_alert'])
            print("alert_counter_dic:", self.alert_counter_dic)
            print("matched_action_list:", matched_action_list)
            for action_obj in matched_action_list:
                #开始报警
                if time.time() - self.alert_counter_dic[action_obj.id][host_id]['last_alert'] >= action_obj.interval:
                    print("该报警了.......", time.time() - self.alert_counter_dic[action_obj.id][host_id]['last_alert'],
                          action_obj.interval)
                    for action_operation in action_obj.operations.select_related().order_by('step'):
                        if action_operation.step > self.alert_counter_dic[action_obj.id][host_id]['counter']:
                            print("##################alert action:%s" %action_operation.action_type, action_operation.notifiers)
                            action_func = getattr(self,'action_%s'% action_operation.action_type)
                            action_func(action_obj,action_operation,host_id,self.trigger_data)

                            #报警完成后要更新时间
                            self.alert_counter_dic[action_obj.id][host_id]['last_alert'] = time.time()
                            #记录报警日志
                            self.record_log(action_obj,action_operation,host_id,self.trigger_data)
                            break










