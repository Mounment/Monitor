#!/usr/bin/env python
# -*- coding: utf-8 -*-
# __author__= 'luhj'

from django.conf.urls import url

from  monitor import views

urlpatterns = [
    url(r'^triggers/$',views.triggers,name='triggers' ),
    url(r'hosts/$',views.hosts ,name='hosts'),
    url(r'host_groups/$',views.host_groups ,name='host_groups'),
    url(r'hosts/(\d+)/$',views.host_detail ,name='host_detail'),
    url(r'trigger_list/$',views.trigger_list ,name='trigger_list'),
]