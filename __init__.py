# -*- coding: utf-8 -*-
def classFactory(iface):
    from .plugin import S57ManagerPlugin
    return S57ManagerPlugin(iface)
