# -*- coding: utf-8 -*-
from . import resources_rc

def classFactory(iface):
    from .plugin import S57ManagerPlugin
    return S57ManagerPlugin(iface)
