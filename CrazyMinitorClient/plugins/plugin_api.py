#!/usr/bin/env python
# -*- coding: utf-8 -*-
# __author__= 'luhj'
from plugins.linux import cpu_mac,memory,network,host_alive,cpu,load



def LinuxCpuPlugin():
    return cpu.monitor()

def host_alive_check():
    return host_alive.monitor()

def getMacCpu():
    return cpu_mac.monitor()

def LinuxNetworkPlugin():
    return network.monitor()

def LinuxMemoryPlugin():
    return memory.monitor()

def get_linux_load():
    return load.monitor()

