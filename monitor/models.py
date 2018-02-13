from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class Host(models.Model):
    '''主机表'''
    name = models.CharField(max_length=64,unique=True)
    ip_addr = models.GenericIPAddressField(unique=True)
    host_groups = models.ManyToManyField('HostGroup',blank=True)
    templates = models.ManyToManyField('Template',blank=True)
    monitored_by_choices = (('agent','Agent'),('snmp','Snmp'),('wget','Wget'))
    monitored_by = models.CharField(u'监控方式',max_length=32,choices=monitored_by_choices)
    status_choices = ((1,'Online'),(2,'Down'),(3,'Unreachable'),(5,'Problem'))
    host_alive_check_interval = models.IntegerField(u'主机存活状态检测间隔',default=30)
    status = models.IntegerField(u'状态',choices=status_choices,default=1)
    memo = models.TextField(u'备注',null=True,blank=True)

    def __str__(self):
        return self.name


class HostGroup(models.Model):
    '''主机组'''
    name = models.CharField(max_length=64,unique=True)
    templates = models.ManyToManyField('Template',blank=True)
    memo = models.TextField(u'备注', null=True, blank=True)

    def __str__(self):
        return self.name

class ServiceIndex(models.Model):
    '''监控指标'''
    name = models.CharField(max_length=64)
    key = models.CharField(max_length=64,unique=True)
    data_type_choice = (('int','int'),('float','float'),('str','string'))
    data_type = models.CharField(u'指标数据类型',max_length=32,choices=data_type_choice,default='int')
    memo = models.TextField(u'备注', null=True, blank=True)

    def __str__(self):
        return "%s.%s" % (self.name, self.key)


class Service(models.Model):
    '''监控服务'''
    name = models.CharField(u'服务名称',max_length=64,unique=True)
    interval = models.IntegerField(u'监控间隔',default=60)
    plugin_name = models.CharField(u'插件名称',max_length=64,default='N/A')
    items = models.ManyToManyField('ServiceIndex',verbose_name='指标列表',blank=True)
    has_sub_service = models.BooleanField(default=False,
                                          help_text='如果一个服务还有独立的子服务 ,选择这个,比如 网卡服务有多个独立的子网卡')
    memo = models.TextField(u'备注', null=True, blank=True)

    def __str__(self):
        return self.name

class Template(models.Model):
    '''监控配置模板'''
    name = models.CharField(u'模板名称',max_length=64,unique=True)
    services = models.ManyToManyField('Service',verbose_name='服务列表')
    triggers = models.ManyToManyField('Trigger',verbose_name='触发器列表',blank=True)
    def __str__(self):
        return self.name


class UserProfile(models.Model):
    '''用户'''
    user = models.OneToOneField(User)
    name = models.CharField(max_length=64,blank=True,null=True)


class Trigger(models.Model):
    '''监控触发器'''
    name = models.CharField(u'触发器名称',max_length=64)
    severity_choices = ((1,'Infomation'),(2,'Warning'),(3,'Average'),(4,'High'),(5,'Diaster'))
    severity = models.IntegerField(u'告警级别',choices=severity_choices)
    enabled = models.BooleanField(default=True)
    memo = models.TextField(u'备注', null=True, blank=True)

    def __str__(self):
        return "<serice:%s, severity:%s>" % (self.name, self.get_severity_display())

class TriggerExpression(models.Model):
    '''触发器表达式'''
    trigger = models.ForeignKey('Trigger',verbose_name=u'所述触发器')
    service = models.ForeignKey('Service',verbose_name=u'关联服务')
    service_index = models.ForeignKey('ServiceIndex',verbose_name=u'关联服务指标')
    specified_index_key = models.CharField(verbose_name=u'只监控专门指定的指标key',
                                           max_length=64,blank=True,null=True)
    operator_type_choices = (('eq','='),('gt','>'),('lt','<'))
    operator_type = models.CharField(u'运算符',choices=operator_type_choices,max_length=32)
    data_calc_type_choices = (('avg','Average'),('max','Max'),('hit','Hit'),('last','Last'))
    data_calc_func = models.CharField(u'数据处理方式',choices=data_calc_type_choices,max_length=64)
    data_calc_args = models.CharField(u'函数传入参数',max_length=64,
                                      help_text=u'若是多个参数,则用,号分开,第一个值是时间')
    threshold = models.IntegerField(u'阈值')
    logic_type_choices = (('or','OR'),('and','AND'))
    logic_type = models.CharField(u'与一个条件的逻辑关系',choices=logic_type_choices,max_length=32,
                                  blank=True,null=True)

    def __str__(self):
        return "%s %s(%s(%s))" % (self.service_index, self.operator_type, self.data_calc_func, self.data_calc_args)


class Action(models.Model):
    '''报警策略'''
    name = models.CharField(max_length=64,unique=True)
    host_groups = models.ManyToManyField('HostGroup',blank=True)
    hosts = models.ManyToManyField('Host',blank=True)
    triggers = models.ManyToManyField('Trigger',blank=True,help_text=u'想让哪些trigger触发当前报警动作')
    interval = models.IntegerField(u'告警时间(s)',default=300)
    operations = models.ManyToManyField('ActionOperation',verbose_name='报警动作')
    recover_notice = models.BooleanField(u'故障恢复后发送通知消息',default=True)
    recover_subject = models.CharField(max_length=128,blank=True,null=True)
    recover_message = models.TextField(null=True,blank=True)
    enabled = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class ActionOperation(models.Model):
    '''报警动作'''
    name = models.CharField(max_length=64)
    step = models.SmallIntegerField(u'第n次告警',default=1,help_text='当trigger触发次数小于这个值时就执行这条记录里报警方式')
    action_type_choices = (('email','Email'),('sms','SMS'),('script','SCRIPT'))
    action_type = models.CharField(u'动作类型',choices=action_type_choices,default='email',max_length=64)
    notifiers = models.ManyToManyField('UserProfile',verbose_name=u'通知对象',blank=True)
    _msg_format = '''Host({hostname},{ip}) service({service_name}) has issue,msg:{msg}'''
    msg_format = models.TextField(u'消息格式',default=_msg_format)

    def __str__(self):
        return self.name

class EventLog(models.Model):
    '''存储报警及其日志'''
    event_type_choices = ((0,'报警事件'),(1,'维护事件'))
    event_type = models.SmallIntegerField(choices=event_type_choices,default=0)
    host = models.ForeignKey('Host')
    trigger = models.ForeignKey('Trigger',blank=True,null=True)
    log = models.TextField(blank=True,null=True)
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return "host%s  %s" % (self.host, self.log)

