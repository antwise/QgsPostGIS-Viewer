#!/usr/bin/python
# -*- coding: utf-8 -*-

import os, sys, math, imp, fileinput, re
import resources
try:
    from PyQt4.QtSql import QSqlDatabase, QSqlQuery
    from PyQt4.QtGui import ( QAction, QMainWindow, QApplication, QMessageBox, 
        QStatusBar, QFrame, QLabel, QDockWidget, QTreeWidget, QTreeWidgetItem, 
        QPixmap, QIcon, QFont, QMenu, QColorDialog, QAbstractItemView, QFileDialog )
    from PyQt4.QtCore import SIGNAL, Qt, QString, QSharedMemory, QIODevice, QPoint, QObject, QRegExp, QSize
    from PyQt4.QtNetwork import QLocalServer, QLocalSocket

    from qgis.core import QgsApplication, QgsDataSourceURI, QgsVectorLayer, QgsRasterLayer, QgsMapLayerRegistry, QGis, QgsMapLayer, QgsCoordinateTransform, QgsVectorFileWriter
    from qgis.gui import QgsMapCanvas, QgsMapToolPan, QgsMapToolZoom, QgsMapCanvasLayer

except ImportError as e:
    print >> sys.stderr, 'E: Qt or QGIS not installed.', e
    print >> sys.stderr, 'E: Exiting ...'
    sys.exit(1)


# A couple of classes for the layer list widget and the layer properties
class LegendItem( QTreeWidgetItem ):
    """ Provide a widget to show and manage the properties of one single layer """
    def __init__( self, parent, canvasLayer ):
        QTreeWidgetItem.__init__( self )
        self.legend = parent
        self.canvasLayer = canvasLayer
        self.canvasLayer.layer().setLayerName( self.legend.normalizeLayerName( unicode( self.canvasLayer.layer().name() ) ) )
        self.setText( 0, self.canvasLayer.layer().name() )
        self.isVect = ( self.canvasLayer.layer().type() == QgsMapLayer.VectorLayer ) # 0: Vector, 1: Raster
        #self.layerId = self.canvasLayer.layer().getLayerID()
        self.layerId = self.canvasLayer.layer().id()

        if self.isVect:
            geom = self.canvasLayer.layer().dataProvider().geometryType()

        self.setCheckState( 0, Qt.Checked )

        pm = QPixmap( 20, 20 )
        icon = QIcon()

        if self.isVect:
            if geom == QGis.WKBPoint or geom == QGis.WKBMultiPoint or geom == QGis.WKBPoint25D or geom == QGis.WKBMultiPoint25D: # Point
                icon.addPixmap( QPixmap( ":/icons/mIconPointLayer.png" ), QIcon.Normal, QIcon.On)
            elif geom == QGis.WKBLineString or geom == QGis.WKBMultiLineString or geom == QGis.WKBLineString25D or geom == QGis.WKBMultiLineString25D: # Polyline
                icon.addPixmap( QPixmap( ":/icons/mIconLineLayer.png"), QIcon.Normal, QIcon.On)
            elif geom == QGis.WKBPolygon or geom == QGis.WKBMultiPolygon or geom == QGis.WKBPolygon25D or geom == QGis.WKBMultiPolygon25D: # Polygon
                icon.addPixmap( QPixmap( ":/icons/mIconPolygonLayer.png"), QIcon.Normal, QIcon.On)
            else: # Not a valid WKT Geometry
                geom = self.canvasLayer.layer().geometryType() # QGis Geometry
                if geom == QGis.Point: # Point
                    icon.addPixmap( QPixmap( ":/icons/mIconPointLayer.png" ), QIcon.Normal, QIcon.On)
                elif geom == QGis.Line: # Line
                    icon.addPixmap( QPixmap( ":/icons/mIconLineLayer.png"), QIcon.Normal, QIcon.On)
                elif geom == QGis.Polygon: # Polygon
                    icon.addPixmap( QPixmap( ":/icons/mIconPolygonLayer.png"), QIcon.Normal, QIcon.On)
                else:
                    raise RuntimeError, 'Unknown geometry: ' + str( geom )

        else:
            pm = self.canvasLayer.layer().previewAsPixmap( pm.size() )
            icon.addPixmap( pm )

        self.setIcon( 0, icon )

        self.setToolTip( 0, self.canvasLayer.layer().publicSource() )
        layerFont = QFont()
        layerFont.setBold( True )
        self.setFont( 0, layerFont )

        # Display layer properties
        self.properties = self.getLayerProperties( self.canvasLayer.layer() )
        self.child = QTreeWidgetItem( self )
        self.child.setFlags( Qt.NoItemFlags ) # Avoid the item to be selected
        self.displayLayerProperties()
		

    def getLayerProperties( self, l ):
        """ Create a layer-properties string (l:layer)"""
        print 'I: Generating layer properties...'
        layerSRID = l.crs().description() + ' (' + str( l.crs().postgisSrid() ) + ')'
        extent = l.extent()
        viewCrs = self.legend.canvas.mapRenderer().destinationCrs()		
        viewExtent = self.legend.canvas.mapRenderer().layerToMapCoordinates( l, extent )
        strViewExtent = self.legend.viewParamsView.stringExtent( viewExtent )
        
        if l.type() == QgsMapLayer.VectorLayer : # Vector
            wkbType = ["WKBUnknown","WKBPoint","WKBLineString","WKBPolygon",
                       "WKBMultiPoint","WKBMultiLineString","WKBMultiPolygon",
                       "WKBNoGeometry","WKBPoint25D","WKBLineString25D","WKBPolygon25D",
                       "WKBMultiPoint25D","WKBMultiLineString25D","WKBMultiPolygon25D"]
            tableSource = QgsDataSourceURI(l.source()).table()
            properties = "Source: %s<br>" \
                         "%s <br>" \
                         "Geometry type: %s<br>" \
                         "Number of features: %s<br>" \
                         "Number of fields: %s<br>" \
                         "SRS (EPSG): %s<br>" \
                         "Extent: %s <br>" \
                         "View extent: %s " \
                          % ( l.source(), self.extractSqlQuery( tableSource ), wkbType[l.wkbType()], l.featureCount(), 
                              l.dataProvider().fields().count(), layerSRID, 
                              extent.toString(), strViewExtent )
        elif l.type() == QgsMapLayer.RasterLayer : # Raster
            rType = [ "GrayOrUndefined (single band)", "Palette (single band)", "Multiband" ]            
            properties = "Source: %s<br>" \
                         "Raster type: %s<br>" \
                         "Width-Height (pixels): %sx%s<br>" \
                         "Bands: %s<br>" \
                         "SRS (EPSG): %s<br>" \
                         "Extent: %s <br>" \
                         "View extent: %s " \
                         % ( l.source(), rType[l.rasterType()], l.width(), l.height(),
                             l.bandCount(), layerSRID, extent.toString(), strViewExtent )
            print 'I: Test projections: %i ? %i' % (l.crs().postgisSrid(), viewCrs.postgisSrid())
            if l.crs().postgisSrid() != viewCrs.postgisSrid():
			    properties = properties + "<br> <b><font color='red'>Warning! reprojection raster to EPSG:" + str( viewCrs.postgisSrid() ) + " may be slow!</font></b>"
        return properties		
        
    def displayLayerProperties( self ):
        """ It is required to build the QLabel widget every time it is set """        
        propertiesFont = QFont()
        propertiesFont.setItalic( True )
        propertiesFont.setPointSize( 8 )
        propertiesFont.setStyleStrategy( QFont.PreferAntialias )

        label = QLabel( self.properties )
        label.setTextFormat( Qt.RichText )
        label.setTextInteractionFlags( Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard )
        label.setFont( propertiesFont )
        self.legend.setItemWidget( self.child, 0, label )
        
    def updateProperties( self ):
        """ Update view """  
        self.properties = self.getLayerProperties( self.canvasLayer.layer() )
        label = self.treeWidget().itemWidget(self.child, 0)
        label.setText( self.properties )
        self.child.setSizeHint(0, label.sizeHint())
        self.legend.updateGeometries()

    def nextSibling( self ):
        """ Return the next layer item """
        return self.legend.nextSibling( self )

    def storeAppearanceSettings( self ):
        """ Store the appearance of the layer item """
        self.__itemIsExpanded = self.isExpanded()

    def restoreAppearanceSettings( self ):
        """ Restore the appearance of the layer item """
        self.setExpanded( self.__itemIsExpanded )
        self.displayLayerProperties() # Generate the QLabel widget again
		
    def extractSqlQuery( self , source):
        rx = QRegExp('\\(select row_number\\(\\) over\\(order by 1\\) id, q.\\w+ from  \\((.*)\\) as q\\)')
        if rx.indexIn(source) == -1:
            return 'Table: <b>' + source + '</b>'
	
        return 'SqlQuery: <b>' + rx.cap(1) + '</b>'


class Legend( QTreeWidget ):
    """
      Provide a widget that manages map layers and their properties as tree items
    """
    def __init__( self, canvas, viewParamsView, parent = None ):
        QTreeWidget.__init__( self, parent )

        self.canvas = canvas
        self.viewParamsView = viewParamsView
        self.layers = self.getLayerSet()

        self.bMousePressedFlag = False
        self.itemBeingMoved = None

        # QTreeWidget properties
        self.setSortingEnabled( False )
        self.setDragEnabled( False )
        self.setAutoScroll( False )
        #self.setVerticalScrollMode( QAbstractItemView.ScrollPerPixel )
        self.setHeaderHidden( True )
        self.setRootIsDecorated( True )
        self.setContextMenuPolicy( Qt.CustomContextMenu )

        self.connect( self, SIGNAL( "customContextMenuRequested(QPoint)" ),
            self.showMenu )
        self.connect( QgsMapLayerRegistry.instance(), SIGNAL("layerWasAdded(QgsMapLayer *)"),
            self.addLayerToLegend )
        self.connect( QgsMapLayerRegistry.instance(), SIGNAL( "removedAll()" ),
            self.removeAll )
        self.connect( QgsMapLayerRegistry.instance(), SIGNAL( "layerWillBeRemoved(QString)" ),
            self.layerRemoved )
        self.connect( self, SIGNAL( "itemChanged(QTreeWidgetItem *,int)" ),
            self.updateLayerStatus )
        self.connect( self, SIGNAL( "currentItemChanged(QTreeWidgetItem *, QTreeWidgetItem *)" ),
            self.currentItemChanged )			
        self.connect( self.viewParamsView, SIGNAL( "viewCrsChanged" ), 
            self.updateInfo )
            
    def setCanvas( self, canvas ):
        """ Set the base canvas """
        self.canvas = canvas

    def showMenu( self, pos ):
        """ Show a context menu for the active layer in the legend """
        item = self.itemAt( pos )
        if item:
            if self.isLegendLayer( item ):
                self.setCurrentItem( item )
                self.menu = self.getMenu( item.isVect, item.canvasLayer )
                self.menu.popup( QPoint( self.mapToGlobal( pos ).x() + 5, self.mapToGlobal( pos ).y() ) )

    def getMenu( self, isVect, canvasLayer ):
        """ Create a context menu for a layer """
        menu = QMenu()
        menu.addAction( QIcon( ":/icons/mActionZoomToLayer.png" ), "&Zoom to layer extent", self.zoomToLayer )
        menu.addSeparator()
        if isVect :
            menu.addAction( QIcon( ":/icons/symbology.png" ), "&Symbology...", self.layerSymbology )
            menu.addAction( QIcon( ":/icons/save.png" ), "&Save as shp...", self.saveLayer )			
        menu.addSeparator()
        menu.addAction( QIcon( ":/icons/collapse.png" ), "&Collapse all", self.collapseAll )
        menu.addAction( QIcon( ":/icons/expand.png" ), "&Expand all", self.expandAll )
        menu.addSeparator()
        menu.addAction( QIcon( ":/icons/removeLayer.png" ), "&Remove layer", self.removeCurrentLayer )
        return menu

    def mousePressEvent(self, event):
        """ Mouse press event to manage the layers drag """
        if ( event.button() == Qt.LeftButton ):
            self.lastPressPos = event.pos()
            self.bMousePressedFlag = True
        QTreeWidget.mousePressEvent( self, event )

    def mouseMoveEvent(self, event):
        """ Mouse move event to manage the layers drag """
        if ( self.bMousePressedFlag ):
            # Set the flag back such that the else if(itemBeingMoved)
            # code part is passed during the next mouse moves
            self.bMousePressedFlag = False

            # Remember the item that has been pressed
            item = self.itemAt( self.lastPressPos )
            if ( item ):
                if ( self.isLegendLayer( item ) ):
                    self.itemBeingMoved = item
                    self.storeInitialPosition() # Store the initial layers order
                    self.setCursor( Qt.SizeVerCursor )
                else:
                    self.setCursor( Qt.ForbiddenCursor )
        elif ( self.itemBeingMoved ):
            p = QPoint( event.pos() )
            self.lastPressPos = p

            # Change the cursor
            item = self.itemAt( p )
            origin = self.itemBeingMoved
            dest = item

            if not item:
                self.setCursor( Qt.ForbiddenCursor )

            if ( item and ( item != self.itemBeingMoved ) ):
                if ( self.yCoordAboveCenter( dest, event.y() ) ): # Above center of the item
                    if self.isLegendLayer( dest ): # The item is a layer
                        if ( origin.nextSibling() != dest ):                            
                            self.moveItem( dest, origin )
                        self.setCurrentItem( origin )
                        self.setCursor( Qt.SizeVerCursor )
                    else:
                        self.setCursor( Qt.ForbiddenCursor )
                else: # Below center of the item
                    if self.isLegendLayer( dest ): # The item is a layer
                        if ( self.itemBeingMoved != dest.nextSibling() ):
                            self.moveItem( origin, dest )
                        self.setCurrentItem( origin )
                        self.setCursor( Qt.SizeVerCursor )
                    else:
                        self.setCursor( Qt.ForbiddenCursor )

    def mouseReleaseEvent( self, event ):
        """ Mouse release event to manage the layers drag """
        QTreeWidget.mouseReleaseEvent( self, event )
        self.setCursor( Qt.ArrowCursor )
        self.bMousePressedFlag = False

        if ( not self.itemBeingMoved ):
            #print "*** Legend drag: No itemBeingMoved ***"
            return

        dest = self.itemAt( event.pos() )
        origin = self.itemBeingMoved
        if ( ( not dest ) or ( not origin ) ): # Release out of the legend
            self.checkLayerOrderUpdate()
            return

        self.checkLayerOrderUpdate()
        self.itemBeingMoved = None

    def addLayerToLegend( self, canvasLayer ):	
        """ Slot. Create and add a legend item based on a layer """
        legendLayer = LegendItem( self, QgsMapCanvasLayer( canvasLayer ) )
        self.addLayer( legendLayer )

    def addLayer( self, legendLayer ):
        """ Add a legend item to the legend widget """
        self.insertTopLevelItem ( 0, legendLayer )
        self.expandItem( legendLayer )
        self.setCurrentItem( legendLayer )
        self.updateLayerSet()

    def updateLayerStatus( self, item ):
        """ Update the layer status """
        if ( item ):
            if self.isLegendLayer( item ): # Is the item a layer item?
                for i in self.layers:
                    if i.layer().id() == item.layerId:
                        if item.checkState( 0 ) == Qt.Unchecked:
                            i.setVisible( False )
                        else:
                            i.setVisible( True )
                        self.canvas.setLayerSet( self.layers )
                        return

    def updateInfo( self ):
        """ Update info all layers """
        print 'I: update Info, items:%i ' % self.topLevelItemCount() 
        for i in range( self.topLevelItemCount() ):
            self.topLevelItem( i ).updateProperties()
		
    def currentItemChanged( self, newItem, oldItem ):
        """ Slot. Capture a new currentItem and emit a SIGNAL to inform the new type 
            It could be used to activate/deactivate GUI buttons according the layer type
        """
        layerType = None

        if self.currentItem():
            if self.isLegendLayer( newItem ):
                layerType = newItem.canvasLayer.layer().type()
                self.canvas.setCurrentLayer( newItem.canvasLayer.layer() )
            else:
                layerType = newItem.parent().canvasLayer.layer().type()
                self.canvas.setCurrentLayer( newItem.parent().canvasLayer.layer() )

        self.emit( SIGNAL( "activeLayerChanged" ), layerType )

    def zoomToLayer( self ):
        """ Slot. Manage the zoomToLayer action in the context Menu """
        self.zoomToLegendLayer( self.currentItem() )

    def removeCurrentLayer( self ):
        """ Slot. Manage the removeCurrentLayer action in the context Menu """
        QgsMapLayerRegistry.instance().removeMapLayer( self.currentItem().canvasLayer.layer().id() )
        self.removeLegendLayer( self.currentItem() )
        self.updateLayerSet()

    def layerSymbology( self ):
        """ Change the features color of a vector layer """
        legendLayer = self.currentItem()
        
        if legendLayer.isVect == True:
            geom = legendLayer.canvasLayer.layer().geometryType() # QGis Geometry
            for i in self.layers:
                if i.layer().id() == legendLayer.layerId:
                    color = QColorDialog.getColor( i.layer().rendererV2().symbols()[ 0 ].color(), None )
                    break

            if color.isValid():
                pm = QPixmap()
                iconChild = QIcon()
                legendLayer.canvasLayer.layer().rendererV2().symbols()[ 0 ].setColor( color )                                       
                self.canvas.refresh()

    def saveLayer( self ):
        """ Save current vector layer """
        layer = self.currentItem().canvasLayer.layer()	
        if not layer.isValid():
            return 	  			
			
        fileName = QFileDialog.getSaveFileName (None, "Save layer", "", "*.shp")	
        if len(fileName) == 0:
            return 	  		
			
        error = QgsVectorFileWriter.writeAsVectorFormat( layer, fileName, "utf-8", None, "ESRI Shapefile")
        if error != QgsVectorFileWriter.NoError:
            QMessageBox.warning(None, title, "Cannot save " + fileName) 	  		
	
    def zoomToLegendLayer( self, legendLayer ):
        """ Zoom the map to a layer extent """
        for i in self.layers:
            if i.layer().id() == legendLayer.layerId:
                extent = i.layer().extent()
                extent.scale( 1.05 )
                self.canvas.setExtent( extent )
                self.canvas.refresh()
                break

    def removeLegendLayer( self, legendLayer ):
        """ Remove a layer item in the legend """
        if self.topLevelItemCount() == 1:
            self.clear()
        else: # Manage the currentLayer before the remove
            indice = self.indexOfTopLevelItem( legendLayer )
            if indice == 0:
                newCurrentItem = self.topLevelItem( indice + 1 )
            else:
                newCurrentItem = self.topLevelItem( indice - 1 )

            self.setCurrentItem( newCurrentItem )
            self.takeTopLevelItem( self.indexOfTopLevelItem( legendLayer ) )

    def removeAll( self ):
        """ Remove all legend items """
        self.clear()
        self.updateLayerSet()
		
    def layerRemoved( self , idLayer):	
        print 'layer try removed ', idLayer		
        for i in range( self.topLevelItemCount() ):
            item = self.topLevelItem( i )
            if item.canvasLayer.layer().id() == idLayer:
                print 'try remove...', idLayer
                self.removeLegendLayer( item )
                self.updateLayerSet()
                return
        
			
    def updateLayerSet( self ):
        """ Update the LayerSet and set it to canvas """
        self.layers = self.getLayerSet()
        self.canvas.setLayerSet( self.layers )

    def getLayerSet( self ):
        """ Get the LayerSet by reading the layer items in the legend """
        layers = []
        for i in range( self.topLevelItemCount() ):
            layers.append( self.topLevelItem( i ).canvasLayer )
        return layers

    def activeLayer( self ):
        """ Return the selected layer """
        if self.currentItem():
            if self.isLegendLayer( self.currentItem() ):
                return self.currentItem().canvasLayer
            else:
                return self.currentItem().parent().canvasLayer
        else:
            return None

    def collapseAll( self ):
        """ Collapse all layer items in the legend """
        for i in range( self.topLevelItemCount() ):
            item = self.topLevelItem( i )
            self.collapseItem( item )

    def expandAll( self ):
        """ Expand all layer items in the legend """
        for i in range( self.topLevelItemCount() ):
            item = self.topLevelItem( i )
            self.expandItem( item )

    def isLegendLayer( self, item ):
        """ Check if a given item is a layer item """
        return not item.parent()

    def storeInitialPosition( self ):
        """ Store the layers order """
        self.__beforeDragStateLayers = self.getLayerIDs()

    def getLayerIDs( self ):
        """ Return a list with the layers ids """
        layers = []
        for i in range( self.topLevelItemCount() ):
            item = self.topLevelItem( i )
            layers.append( item.layerId )
        return layers

    def nextSibling( self, item ):
        """ Return the next layer item based on a given item """
        for i in range( self.topLevelItemCount() ):
            if item.layerId == self.topLevelItem( i ).layerId:
                break
        if i < self.topLevelItemCount():                                            
            return self.topLevelItem( i + 1 )
        else:
            return None

    def moveItem( self, itemToMove, afterItem ):
        """ Move the itemToMove after the afterItem in the legend """
        itemToMove.storeAppearanceSettings() # Store settings in the moved item
        self.takeTopLevelItem( self.indexOfTopLevelItem( itemToMove ) )
        self.insertTopLevelItem( self.indexOfTopLevelItem( afterItem ) + 1, itemToMove )
        itemToMove.restoreAppearanceSettings() # Apply the settings again
        self.updatePropertiesWidget() # Regenerate all the QLabel widgets for displaying purposes

    def updatePropertiesWidget(self):
        """ Weird function to create QLabel widgets for refreshing the properties 
            It is required to avoid a disgusting overlap in QLabel widgets
        """
        for i in range( self.topLevelItemCount() ):
            item = self.topLevelItem( i )
            item.displayLayerProperties()
            
    def checkLayerOrderUpdate( self ):
        """
            Check if the initial layers order is equal to the final one.
            This is used to refresh the legend in the release event.
        """
        self.__afterDragStateLayers = self.getLayerIDs()
        if self.__afterDragStateLayers != self.__beforeDragStateLayers:
            self.updateLayerSet()
            
    def yCoordAboveCenter( self, legendItem, ycoord ):
        """
            Return a bool to know if the ycoord is in the above center of the legendItem

            legendItem: The base item to get the above center and the below center
            ycoord: The coordinate of the comparison
        """
        rect = self.visualItemRect( legendItem )
        height = rect.height()
        top = rect.top()
        mid = top + ( height / 2 )
        if ( ycoord > mid ): # Bottom, remember the y-coordinate increases downwards
            return False
        else: # Top
            return True

    def normalizeLayerName( self, name ):
        """ Create an alias to put in the legend and avoid to repeat names """
        # Remove the extension
        if len( name ) > 4:
            if name[ -4 ] == '.':
                name = name[ :-4 ]
        return self.createUniqueName( name )

    def createUniqueName( self, name ):
        """ Avoid to repeat layers names """
        import re
        name_validation = re.compile( "\s\(\d+\)$", re.UNICODE ) # Strings like " (1)"

        bRepetida = True
        i = 1
        while bRepetida:
            bRepetida = False

            # If necessary add a sufix like " (1)" to avoid to repeat names in the legend
            for j in range( self.topLevelItemCount() ):
                item = self.topLevelItem( j )
                if item.text( 0 ) == name:
                    bRepetida = True
                    if name_validation.search( name ): # The name already have numeration
                        name = name[ :-4 ]  + ' (' + str( i ) + ')'
                    else: # Add numeration because the name doesn't have it
                        name = name + ' (' + str( i ) + ')'
                    i += 1
        return name


