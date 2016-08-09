# -*- coding: utf-8 -*-

"""
/***************************************************************************
Name                 : Last PGAdmin Query
Description          : Load a PostGIS layer using a last executed pgadmin query 
Date                 : November 24, 2014

 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""

def name():
	return "Last Pgadmin Query"

def description():
	return "Load a PostGIS layer using a last executed pgadmin query "

def version():
	return "Version 0.0.1"

def qgisMinimumVersion():
	return "0.0.1"

def classFactory(iface, host=None, port=None, dbname=None, user=None, passwd=None):
	from ManagerPlugin import ManagerPlugin
	return ManagerPlugin(iface, host, port, dbname, user, passwd)
