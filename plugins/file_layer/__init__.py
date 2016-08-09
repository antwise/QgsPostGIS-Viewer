# -*- coding: utf-8 -*-

"""
/***************************************************************************
Name                 : FileLayer
Description          : Support Raster/Vector files
Date                 : February, 2016

 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""

def name():
	return "FileLayer"

def description():
	return "Support Raster/Vector files"

def version():
	return "Version 0.0.1"

def qgisMinimumVersion():
	return "0.0.1"

def classFactory(iface, host=None, port=None, dbname=None, user=None, passwd=None):
	from ManagerPlugin import ManagerPlugin
	return ManagerPlugin(iface, host, port, dbname, user, passwd)
