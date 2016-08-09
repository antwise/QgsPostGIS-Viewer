# -*- coding: utf-8 -*-

from PyQt4.QtCore import *
from PyQt4.QtGui import *

from qgis.core import *

import os
import resources

class ManagerPlugin:

  def __init__(self, iface, host, port, dbname, user, passwd):
    # Save reference to the QGIS interface
    self.iface = iface
  
  def initGui(self):
    # Create action that will start plugin configuration
    self.actionAddRasterLayer = QAction(QIcon(":/icons/raster.png"), "Add raster layer", self.iface.mainWindow())
    QObject.connect(self.actionAddRasterLayer, SIGNAL("triggered()"), self.addRasterLayer)
    self.iface.addToolBarIcon(self.actionAddRasterLayer)
	
    self.actionAddVectorLayer = QAction(QIcon(":/icons/vector.png"), "Add vector layer", self.iface.mainWindow())
    QObject.connect(self.actionAddVectorLayer, SIGNAL("triggered()"), self.addVectorLayer)
    self.iface.addToolBarIcon(self.actionAddVectorLayer)	

  def unload(self):
    self.iface.removeToolBarIcon(self.actionAddRasterLayer)
    self.iface.removeToolBarIcon(self.actionAddVectorLayer)	
	
  def addRasterLayer(self):
    self.openRaster( self.openFile("Gdal raster files (*.tiff *.img *.jpg *.xml *.*)") )
	
  def addVectorLayer(self):
    self.openVector( self.openFile("Gdal vector files (*.shp *.*)") )	
	
  def openFile(self, extensions):
    return QFileDialog.getOpenFileName(self.iface.mainWindow(), "Open raster File", "", extensions)
	
  def openRaster(self, fileRaster):
    if len(fileRaster) == 0:
        return 	  
		
    print 'I:Try add raster layer', fileRaster.toLatin1().data()	
    fileInfo = QFileInfo(fileRaster)
    layer = QgsRasterLayer( fileRaster, fileInfo.fileName() )
    self.addLayer( layer )
	
  def openVector(self, fileName):
    if len(fileName) == 0:
        return 	  
		
    print 'I:Try add vector layer', fileName.toLatin1().data()	
    fileInfo = QFileInfo(fileName)
    layer = QgsVectorLayer( fileName, fileInfo.fileName(), "ogr" ) 	
    self.addLayer( layer )
	
  def addLayer(self, layer):
    if not layer.isValid() :
        print "Failed to load"	
        return 	
    
    QgsMapLayerRegistry.instance().addMapLayer( layer )
