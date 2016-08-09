#!/usr/bin/python
# -*- coding: utf-8 -*-
try:
    from PyQt4.QtCore import SIGNAL, Qt, QString, QObject	
    from qgis.core import QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsPoint, QgsMapToPixel, QgsMapRenderer
    from qgis.gui import QgsMapCanvas
	
except ImportError as e:
    print >> sys.stderr, 'E: Qt not installed.', e
    print >> sys.stderr, 'E: Exiting ...'
    sys.exit(1)	


class ViewParamsString( QObject ):
    """ Class to view formatted string coords and scale """
	
    (
	ModeDegree, 
	ModeDegreeMinutesSecundes, 
	ModeMetric, 
	ModeCount
	) = range(4)
	
    def __init__( self, canvas ):
        QObject.__init__( self )
        self.m_mode = self.ModeMetric
        self.m_canvas = canvas
        self.m_transformToCoordCrs = QgsCoordinateTransform()
        self.connect( self.m_canvas, SIGNAL( "scaleChanged(double)" ), self.changeScale )
        self.connect( self.m_canvas, SIGNAL( "xyCoordinates(const QgsPoint&)" ), self.changeXY )
        self.connect( self.m_canvas, SIGNAL( "destinationCrsChanged()" ), self.updateCrs )			
		
        self.setMode(self.ModeMetric)		

    def mode( self ):
        return self.m_mode

    def setMode( self, mode ):
        self.m_mode = mode % self.ModeCount
        self.updateCrs()
        print 'I: set mode view to %i!' % self.m_mode		
	
    def changeScale( self, scale ):
        self.emit( SIGNAL("scaleChanged(QString)"), self.tr("Scale 1:") + self.formatNumber( scale ) )	

    def changeXY( self, p ):
        self.emit( SIGNAL("xyCoordinates(QString)"), self.stringCoord(p) )	
		
    def updateCrs( self ):
        viewCrs = self.m_canvas.mapRenderer().destinationCrs()
			
        if ( viewCrs.geographicFlag() and self.m_mode == self.ModeMetric):
			self.m_mode = self.ModeDegree
			
        if ( not viewCrs.geographicFlag() and self.m_mode == self.ModeMetric): 	# Metric
            coordCrs = viewCrs 
        else: # Degrees
            coordCrs = QgsCoordinateReferenceSystem( viewCrs.geographicCRSAuthId() )
			
        self.m_transformToCoordCrs = QgsCoordinateTransform(viewCrs, coordCrs)
        self.emit( SIGNAL("viewCrsChanged") )
        self.changeXY( self.lastMouseCoord() )				
		
    def lastMouseCoord( self ):
        return self.m_canvas.mapRenderer().coordinateTransform().toMapCoordinates(self.m_canvas.mouseLastXY())				
		
    def stringCoord( self, p ):
        pntCoord = self.m_transformToCoordCrs.transform( p )
		
        if ( self.m_mode == self.ModeDegree ): 
            return pntCoord.toDegreesMinutes(2)
			
        if ( self.m_mode == self.ModeDegreeMinutesSecundes ): 
            return pntCoord.toDegreesMinutesSeconds(0)
			  
        meterStr = self.tr("m")  
        return self.formatNumber( p.x() ) + meterStr + " | " \
             + self.formatNumber( p.y() ) + meterStr 

    def stringExtent( self, r ):
        strPntBottomLeft = self.stringCoord( QgsPoint(r.xMinimum(), r.yMinimum()) )
        strPntTopRight = self.stringCoord( QgsPoint(r.xMaximum(), r.yMaximum()) )		
        return strPntBottomLeft + " : " + strPntTopRight
		
    def transformedExtent( self, r ):
        return self.m_transformToCoordCrs.transform( r )
				
    # Some helpful functions
    def formatNumber(self, number, precision=0, group_sep=' ', decimal_sep=',' ):
        """
        number: Number to be formatted 
        precision: Number of decimals
        group_sep: Miles separator
        decimal_sep: Decimal separator
        """
        number = ( '%.*f' % ( max( 0, precision ), number ) ).split( '.' )
        integer_part = number[ 0 ]

        if integer_part[ 0 ] == '-':
            sign = integer_part[ 0 ]
            integer_part = integer_part[ 1: ]
        else:
            sign = ''

        if len( number ) == 2:
            decimal_part = decimal_sep + number[ 1 ]
        else:
            decimal_part = ''

        integer_part = list( integer_part )
        c = len( integer_part )

        while c > 3:
            c -= 3
        integer_part.insert( c, group_sep )

        return sign + ''.join( integer_part ) + decimal_part
