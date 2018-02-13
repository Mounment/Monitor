#!/usr/bin/env python
# -*- coding: utf-8 -*-
# __author__= 'luhj'

from core.client import ClientHandler



class command_handler(object):
    def __init__(self,sys_argv):
        self.sys_argv = sys_argv
        if len(sys_argv) < 2:
            self.help_message()
        self.command_allowcator()


    def command_allowcator(self):
        print(self.sys_argv[1])
        if hasattr(self,self.sys_argv[1]):
            func = getattr(self,self.sys_argv[1])
            return func()
        else:
            print('命令不存在')
            self.help_message()

    def help_message(self):
        valid_commands = '''
                start       start monitor client
                stop        stop monitor client

                '''
        exit(valid_commands)

    def start(self):
        client = ClientHandler()
        client.forever_run()

    def stop(self):
        print('关闭客户端')
        exit()