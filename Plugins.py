#!/usr/bin/python
# -*- coding: utf-8 -*-

import os, sys, math, imp, fileinput, re

try:
    from PyQt4.QtCore import SIGNAL, Qt, QString, QIODevice, QPoint, QObject
	
    from qgis.core import QgsApplication, QgsDataSourceURI, QgsVectorLayer, QgsRasterLayer, QgsMapLayerRegistry, QGis
    from qgis.gui import QgsMapCanvas, QgsMapToolPan, QgsMapToolZoom, QgsMapCanvasLayer
	
    from SqlLayer import SqlLayer	
except ImportError as e:
    print >> sys.stderr, 'E: Qt not installed.', e
    print >> sys.stderr, 'E: Exiting ...'
    sys.exit(1)	


# Class to expose qgis objects and functionalities to plugins
class QgisInterface( QObject ):
    """ Class to expose qgis objects and functionalities to plugins """
    def __init__( self, myApp, canvas, sqlLayer ):
        QObject.__init__( self )
        self.myApp = myApp
        self.canvas = canvas
        self.toolBarPlugins = None
        self.sqlLayer = sqlLayer
		
    def __del__(self):
        self.sqlLayer.removeScheme()
		
    def mapCanvas( self ):
        """ Return a pointer to the map canvas """
        return self.canvas

    def mainWindow( self ):
        """ Return a pointer to the main window (instance of QgisApp in case of QGIS) """
        return self.myApp
		
    def viewParamsView( self ):
        """ Return a pointer to view params """
        return self.myApp.viewParamsView		
		
    def sqlLayerController( self ):
        """ Return a sql controller """
        return self.sqlLayer		
		
	#      Access to widgets mainwindow
    def addToolBarIcon( self, qAction ):
        """ Add an icon to the plugins toolbar """
        if not self.toolBarPlugins:
            self.toolBarPlugins = self.addToolBar( "Plugins" )
        self.toolBarPlugins.addAction( qAction )

    def removeToolBarIcon( self, qAction ):
        """ Remove an action (icon) from the plugin toolbar """
        if not self.toolBarPlugins:
            return
        self.toolBarPlugins.removeAction( qAction )

    def addToolBar( self, name ):
        """ Add toolbar with specified name """
        toolBar = self.myApp.addToolBar( name )
        toolBar.setObjectName( name )
        return toolBar
		
    def removeToolBar( self, toolbar ):
        """ Remove toolbar from app"""
        toolBar = self.myApp.removeToolBar( toolbar )

    def addDockWidget( self, area, dockwidget ):
        """ Add a dock widget to the main window """
        self.myApp.addDockWidget( area, dockwidget )
        dockwidget.show()
		
    def removeDockWidget( self, dockwidget ):
        """ Remove a dock widget from the main window """
        self.myApp.removeDockWidget( dockwidget )
        	

# Class to manage plugins (Read and load the existing plugins)
class Plugins():
    """ Class to manage plugins (Read and load existing plugins) """
    def __init__( self, myApp, canvas, host, port, dbname, user, passwd ):
        self.qgisInterface = QgisInterface( myApp, canvas, SqlLayer(host, dbname, user, passwd, port) )
        self.myApp = myApp
        self.plugins = []
        self.pluginsDirName = 'plugins'
        regExpString = '^def +classFactory\(.*iface.*(\):)$' # To find the classFactory line

        """ Validate that it is a plugins folder and loads them into the application """
        dir_plugins = os.path.join( os.path.dirname(__file__), self.pluginsDirName )

        if os.path.exists( dir_plugins ):
            for root, dirs, files in os.walk( dir_plugins ):
                bPlugIn = False

                if not dir_plugins == root: 
                    if '__init__.py' in files: 
                        for line in fileinput.input( os.path.join( root, '__init__.py' ) ):
                            linea = line.strip()
                            if re.match( regExpString, linea ):
                                bPlugIn = True
                                break
                        fileinput.close()

                        if bPlugIn:
                            plugin_name = os.path.basename( root )
                            f, filename, description = imp.find_module( plugin_name, [ dir_plugins ] )

                            try: 
                                package = imp.load_module( plugin_name, f, filename, description )
                                self.plugins.append( package.classFactory( self.qgisInterface, host, port, dbname, user, passwd ) )
                            except Exception, e:
                                print 'E: Plugin ' + plugin_name + ' could not be loaded. ERROR!:',e
                            else:
                                self.plugins[ -1 ].initGui()
                                print 'I: Plugin ' + plugin_name + ' successfully loaded!'
        else:
            print "Plugins folder not found."
