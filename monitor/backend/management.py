#!/usr/bin/env python
# -*- coding: utf-8 -*-
# __author__= 'luhj'
import os,sys
import django
django.setup()
from monitor.backend import data_processing,trigger_handler
from django.conf import settings

class ManagementUnility(object):

    def __init__(self,argv):
        self.argv = argv or sys.argv[:]
        self.prog_name = os.path.basename(self.argv[0])
        self.settings_exception = None
        self.registered_actions = {
            'start':self.start,
            'stop':self.stop,
            'trigger_watch':self.trigger_watch
        }
        self.argv_check()

    def argv_check(self):
        if len(self.argv) < 2:
            self.main_help_text()
        if self.argv[1] not in self.registered_actions:
            self.main_help_text()
        else:
            self.registered_actions[sys.argv[1]]()

    def start(self):
        '''开启服务,并检测主机是否存活'''
        reactor = data_processing.DataHandler(settings)
        reactor.looping()

    def stop(self):
        exit('退出监控系统')

    def trigger_watch(self):
        trigger_watch= trigger_handler.TriggerHandler(settings)
        trigger_watch.start_watching()

    def main_help_text(self,command_only=False):
        if not command_only:
            print("supported commands as flow:")
            for k,v in self.registered_actions.items():
                print("    %s%s" % (k.ljust(20), v.__doc__))
            exit()

    def execute(self):
        ''''''


def execute_from_command_line(argv=None):
    unitity = ManagementUnility(argv)
    unitity.execute()

