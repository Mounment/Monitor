#!/usr/bin/env python
# -*- coding: utf-8 -*-
# __author__= 'luhj'

import redis

def redis_conn(django_settings):
    #print(django_settings.REDIS_CONN)
    pool = redis.ConnectionPool(host=django_settings.REDIS_CONN['HOST'],
                                port=django_settings.REDIS_CONN['PORT'],
                                db=django_settings.REDIS_CONN['DB'])
    r = redis.Redis(connection_pool=pool)
    return  r