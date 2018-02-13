#!/usr/bin/env python
# -*- coding: utf-8 -*-
# __author__= 'luhj'



configs = {
    'HostID':1,
    'Server':'127.0.0.1',
    'ServerPort':8000,
    'urls':{
        'get_configs' : ['api/client/config','get'],
        'service_report' : ['api/client/service/report/','post']
    },
    'RequireTimeOut':30,
    'ConfigUpdateInterval': 300
}