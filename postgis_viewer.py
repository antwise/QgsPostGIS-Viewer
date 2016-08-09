#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Simple PostGIS viewer based on QGIS libs. v.1.2 
Usage: postgis_viewer.py <options>
    
Options:
    -h host
    -p port
    -U user
    -W password
    -d database
    -s schema
    -t table

Prerequisities:
    Qt, QGIS, libqt4-sql-psql

Using as PgAdmin plugin, copy 'postgis_viewer.py' file on PATH and put following 
to 'plugins.ini' (/usr/share/pgadmin3/plugins.ini on Debian):

    Title=View PostGIS layer
    Command=postgis_viewer.py -h $$HOSTNAME -p $$PORT -U $$USERNAME -W $$PASSWORD -d $$DATABASE -s $$SCHEMA -t $$OBJECTNAME
    Description=View PostGIS layer
    Platform=unix
    ServerType=postgresql
    Database=Yes
    SetPassword=Yes

Authors:
        Copyright (c) 2010 by Ivan Mincik, ivan.mincik@gista.sk
        Copyright (c) 2011 German Carrillo, geotux_tuxman@linuxmail.org
        Copyright (c) 2016 Germanov Kostya,  kgermanov@mail.ru

License: GNU General Public License v2.0
"""

import os, sys, math, imp, fileinput
import getopt
import getpass, pickle # import stuff for ipc
import resources

from Plugins import *
from SingletonApp import SingletonApp
from ViewParamsString import ViewParamsString
from SqlLayer import SqlLayer
	
try:
    from PyQt4.QtGui import ( QAction, QMainWindow, QApplication, QMessageBox, 
        QStatusBar, QFrame, QLabel,  
        QIcon, QPushButton, QComboBox, QWidget, QPrintDialog, QPrinter, QPainter, QDialog, QActionGroup)
    from PyQt4.QtCore import SIGNAL, Qt, QString, QObject, QRectF

    from qgis.core import QgsApplication, QgsMapLayer, QgsMapLayerRegistry, QGis, QgsCoordinateReferenceSystem, QgsComposition, QgsComposerMap
    from qgis.gui import QgsMapCanvas, QgsMapToolPan, QgsMapToolZoom, QgsMapCanvasLayer

except ImportError as e:
    print >> sys.stderr, 'E: Qt or QGIS not installed.', e
    print >> sys.stderr, 'E: Exiting ...'
    sys.exit(1)

class ViewerWnd( QMainWindow ):
    def __init__( self, app, dictOpts ):
        QMainWindow.__init__( self )

		# create canvas
        self.canvas = QgsMapCanvas()
        self.canvas.setCanvasColor( Qt.white )
        self.canvas.useImageToRender( True )
        self.canvas.enableAntiAliasing( True )
        crs = QgsCoordinateReferenceSystem(3857, QgsCoordinateReferenceSystem.EpsgCrsId) # By default - Mercator/WGS84
        self.canvas.mapRenderer().setProjectionsEnabled(True)
        self.canvas.mapRenderer().setDestinationCrs(crs)
        self.canvas.setMapUnits( crs.mapUnits()  )	
        self.connect( self.canvas, SIGNAL( "destinationCrsChanged()" ), self.updateComboCrs )		
        self.connect( QgsMapLayerRegistry.instance(), SIGNAL( "layerWasAdded(QgsMapLayer *)" ), self.addedLayer )		
        self.setCentralWidget( self.canvas )	

		# create actions
        actionGroup = QActionGroup(self)
        actionGroup.setExclusive(True)

        actionZoomIn = actionGroup.addAction( QIcon( ":/icons/mActionZoomIn.png" ), self.tr( "Zoom in" ) )
        actionZoomIn.setCheckable( True )
        self.connect(actionZoomIn, SIGNAL( "triggered()" ), self.zoomIn )
		
        actionZoomOut = actionGroup.addAction( QIcon( ":/icons/mActionZoomOut.png" ), self.tr( "Zoom out" ) )
        actionZoomOut.setCheckable( True )
        self.connect(actionZoomOut, SIGNAL( "triggered()" ), self.zoomOut )
		
        actionPan = actionGroup.addAction( QIcon( ":/icons/mActionPan.png" ), self.tr( "Pan" ) )
        actionPan.setCheckable( True )
        self.connect(actionPan, SIGNAL( "triggered()" ), self.pan )
		
        actionPrint = QAction( QIcon( ":/icons/print.png" ), self.tr( "Print" ), self )
        self.connect(actionPrint, SIGNAL( "triggered()" ), self.printMap )

        # Create the toolbar
        self.toolbar = self.addToolBar( self.tr("Map tools") )
        self.toolbar.addAction( actionZoomIn )
        self.toolbar.addAction( actionZoomOut )
        self.toolbar.addAction( actionPan )
        self.toolbar.addAction( actionPrint )

        # Create the map tools
        self.toolPan = QgsMapToolPan( self.canvas )
        self.toolPan.setAction( actionPan )
        self.toolZoomIn = QgsMapToolZoom( self.canvas, False ) # false = in
        self.toolZoomIn.setAction( actionZoomIn )
        self.toolZoomOut = QgsMapToolZoom( self.canvas, True ) # true = out
        self.toolZoomOut.setAction( actionZoomOut )
        
        # Create the statusbar
        self.statusbar = QStatusBar( self )
        self.statusbar.setObjectName( "statusbar" )
        self.statusbar.setSizeGripEnabled( True )
        self.setStatusBar( self.statusbar )

        self.statusbar.addPermanentWidget( QWidget(), 1 )
		
        self.lblScale = QLabel()
        self.lblScale.setFrameStyle( QFrame.StyledPanel )
        self.lblScale.setMinimumWidth( 140 )
        self.statusbar.addPermanentWidget( self.lblScale, 0 )
		
        self.btnXY = QPushButton()
        self.btnXY.setFlat( True )
        self.btnXY.setMinimumWidth( 170 )
        self.statusbar.setSizeGripEnabled( False )
        self.statusbar.addPermanentWidget( self.btnXY, 0 )
        self.connect( self.btnXY, SIGNAL( "clicked()" ), self.changeViewParams )						
		
        self.viewParamsView = ViewParamsString( self.canvas )
        self.lblScale.connect( self.viewParamsView, SIGNAL( "scaleChanged(QString)" ), self.lblScale.setText )
        self.btnXY.connect( self.viewParamsView, SIGNAL( "xyCoordinates(QString)" ), self.btnXY.setText )
		
        self.crsCombo = QComboBox()
        self.crsCombo.setMinimumWidth( 80 )
        self.connect( self.crsCombo, SIGNAL( "currentIndexChanged(int)" ), self.changedCrs )
        self.statusbar.addPermanentWidget( self.crsCombo, 1 )

		# load plugins
        self.plugins = Plugins( self, self.canvas, dictOpts['-h'], dictOpts['-p'], dictOpts['-d'], dictOpts['-U'], dictOpts['-W'] )
				
		# init state
        self.connect( app, SIGNAL( "message" ), self.loadTable )
        self.pan()
        self.loadTable( dictOpts )
   
    def closeEvent(self, event):
        del self.plugins
	
    def zoomIn( self ):
        self.canvas.setMapTool( self.toolZoomIn )

    def zoomOut( self ):
        self.canvas.setMapTool( self.toolZoomOut )

    def pan( self ):
        self.canvas.setMapTool( self.toolPan )
		
    def printMap( self ):
        print 'I: Try print composer'
        printer = QPrinter(QPrinter.HighResolution)
		
        dialog = QPrintDialog(printer, None);
        dialog.setWindowTitle( "Print Map" );
        res = dialog.exec_()		
        if res != QDialog.Accepted :
            return        
	
        mapRenderer = self.canvas.mapRenderer()
        c = QgsComposition(mapRenderer)
        c.setPlotStyle(QgsComposition.Print)
        dpi = c.printResolution()
        dpmm = dpi/25.4
        width = int(dpmm*c.paperWidth())
        height = int(dpmm*c.paperHeight())
        x, y = 0, 0
        w, h = c.paperWidth(), c.paperHeight()
        composerMap = QgsComposerMap(c, x, y, w, h)
        c.addItem(composerMap)
        sourceArea = QRectF(0, 0, c.paperWidth(), c.paperHeight())
        targetArea = QRectF(0, 0, width,height)
		
        p = QPainter()		
        p.begin(printer)
        p.setRenderHint(QPainter.Antialiasing)
        #self.canvas.mapRenderer().render(p)
        c.render(p, targetArea, sourceArea)
        p.end()

    def changedCrs( self,  index ):
        if index == -1 :
            return
			
        srid = int(self.crsCombo.itemData(index).toString())
        print 'I: Try reproject: %i' % srid
		
        newCrs = QgsCoordinateReferenceSystem( srid )
        self.canvas.mapRenderer().setDestinationCrs( newCrs )
        self.canvas.setExtent( self.canvas.fullExtent() )	
		
    def updateComboCrs( self ):
        crs = self.canvas.mapRenderer().destinationCrs( )
        srid = crs.postgisSrid()
        self.addCrs( crs )		
        findIndex = self.crsCombo.findData(srid)				
        if (findIndex != self.crsCombo.currentIndex() and findIndex != -1):
            self.crsCombo.setCurrentIndex(findIndex)
			
    def addCrs( self, crs ):
        srid = crs.postgisSrid()
        findIndex = self.crsCombo.findData(srid)		
        if findIndex != -1:
            return
			
        print 'I: Try add srid: %i  index:%i' % (srid, findIndex)
        textCrs = crs.description() + ' (' + str( srid ) + ')'
        self.crsCombo.addItem( textCrs, srid )  
		
    def changeViewParams( self ):
        self.viewParamsView.setMode( self.viewParamsView.mode() + 1 )
	
    def addedLayer( self, layer ):
        print 'I: Try add layer! '
        if not layer.isValid():
            return
			
        self.addCrs( layer.crs() )		
        if ( (self.canvas.layerCount() == 0) or (layer.type() == QgsMapLayer.RasterLayer) ) :
            self.canvas.mapRenderer().setDestinationCrs(layer.crs())			
				
        extent = layer.extent()
        if extent.isEmpty():
            extent.set( extent.xMaximum() -0.5, extent.yMaximum() -0.5,  extent.xMaximum() +0.5, extent.yMaximum() +0.5);			
        extentTranslated = self.canvas.mapRenderer().layerToMapCoordinates(layer, extent)            
        self.canvas.setExtent( extentTranslated )
		
    def loadTable( self, dictOpts ):
        print 'I: Loading the layer...'
        host = dictOpts['-h']
        port = dictOpts['-p']
        database = dictOpts['-d']
        user = dictOpts['-U']
        passw = dictOpts['-W']		
        schema = dictOpts['-s']				
        table = dictOpts['-t']

        self.setWindowTitle(database + "  " + host + ":" + port)
        if not self.isActiveWindow():
            self.setWindowState(  Qt.WindowActive | Qt.WindowMinimized) 					
            self.setWindowState(  Qt.WindowActive ) 					
            self.activateWindow()            		
            self.raise_() 		
		
        fullName = QString(schema + '.' + table)
        sqlLayer = SqlLayer(host, database, user, passw, port)
        sqlLayer.createSqlLayer( 'select * from ' + fullName, fullName)
	
def main( argv ):
    print 'I: Starting viewer ...'    
    app = SingletonApp( argv )

    dictOpts = { '-h':'', '-p':'5432', '-U':'', '-W':'', '-d':'', '-s':'public', '-t':'' }
    opts, args = getopt.getopt( sys.argv[1:], 'h:p:U:W:d:s:t:', [] )
    dictOpts.update( opts )	

    if app.is_running:
         # Application already running, send message to load data
        app.send_message( dictOpts )
    else:
        # Start the Viewer

        # Set the qgis_prefix according to the current os
        qgis_prefix = ""
        if os.name == "nt": # Windows
            qgis_prefix = os.getenv("OSGEO4W_ROOT", "C:/OSGeo4W") + "/apps/qgis/"
        else: # Linux
            qgis_prefix = os.getenv("OSGEO4W_ROOT", "/usr")
	
        # QGIS libs init
        QgsApplication.setPrefixPath(qgis_prefix, True)
        QgsApplication.initQgis()
            
        # Open viewer
        wnd = ViewerWnd( app, dictOpts )
        wnd.move(100,100)
        wnd.resize(700, 500)
        wnd.show()

        retval = app.exec_()

        # Exit
        QgsApplication.exitQgis()
        print 'I: Exiting ...'
        sys.exit(retval)      

if __name__ == "__main__":
    main( sys.argv )
