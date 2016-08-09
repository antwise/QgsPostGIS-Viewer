# -*- coding: utf-8 -*-

"""
/***************************************************************************
Name                 : WMS/WMTS
Description          : Support WMS/WMTS server 
Date                 : February, 2016

 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""

def name():
	return "Legend"

def description():
	return "Add layers widget"

def version():
	return "Version 0.0.1"

def qgisMinimumVersion():
	return "0.0.1"

def classFactory(iface, host=None, port=None, dbname=None, user=None, passwd=None):
	from ManagerPlugin import ManagerPlugin
	return ManagerPlugin(iface, host, port, dbname, user, passwd)
