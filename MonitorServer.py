#!/usr/bin/env python
# -*- coding: utf-8 -*-
# __author__= 'luhj'
import sys,os

'''报警启动脚本'''
if __name__ == '__main__':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE','MyMonitor.settings')
    from monitor.backend.management import execute_from_command_line

    execute_from_command_line(sys.argv)