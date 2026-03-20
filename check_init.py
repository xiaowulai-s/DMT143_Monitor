#!/usr/bin/env python
# -*- coding: utf-8 -*-
from core.serial_client import DMT143Client
c = DMT143Client('COM3')
attrs = [a for a in dir(c) if a.startswith('_')]
print("属性列表:", attrs)
print("阈值变量:", hasattr(c, '_dewpoint_change_limit'))
