



from django.conf.urls import url,include
from monitor import api_views
urlpatterns = [

    url(r'client/config/(\d+)/$', api_views.client_config),
    url(r'client/service/report/$', api_views.service_report),
    url(r'hosts/status/$', api_views.hosts_status, name='get_hosts_status'),
    url(r'groups/status/$', api_views.hostgroups_status, name='get_hostgroups_status'),
    url(r'graphs/$', api_views.graphs_generator, name='get_graphs')
]