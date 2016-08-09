# -*- coding: utf-8 -*-

"""
/***************************************************************************
Name                 : RT Sql Layer
Description          : Load a PostGIS layer using a custom query
Date                 : March 2, 2010 
copyright            : (C) 2010 by Giuseppe Sucameli (Faunalia)
email                : brush.tyler@gmail.com

 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""

def name():
	return "RT Sql Layer"

def description():
	return "Load a PostGIS layer using a custom query"

def version():
	return "Version 1.0.14"

def qgisMinimumVersion():
	return "1.0.0"

def classFactory(iface, host=None, port=None, dbname=None, user=None, passwd=None):
	from ManagerPlugin import ManagerPlugin
	return ManagerPlugin(iface, host, port, dbname, user, passwd)
