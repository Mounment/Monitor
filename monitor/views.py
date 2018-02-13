from django.shortcuts import render
from monitor import models
# Create your views here.

def dashboard(request):
    '''首页信息'''
    return render(request,'monitor/dashbord.html')

def triggers(request):
    '''触发器信息'''
    return render(request,'monitor/triggers.html')

def host_groups(request):
    '''主机组信息'''
    host_groups = models.HostGroup.objects.all()
    return render(request,'monitor/host_groups.html',locals())

def hosts(request):
    '''主机信息'''
    host_list = models.Host.objects.all()
    return render(request,'monitor/hosts.html',{'host_list':host_list})

def host_detail(request,host_id):
    '''单个主机信息'''
    host_obj = models.Host.objects.get(id=host_id)
    return render(request,'monitor/host_detail.html',{'host_obj':host_obj})

def trigger_list(request):
    '''报警事件的日志记录'''
    host_id = request.GET.get('by_host_id')
    host_obj = models.Host.objects.get(id=host_id)
    alert_list = host_obj.eventlog_set.all().order_by('-date')
    return render(request,'monitor/trigger_list.html',locals())



