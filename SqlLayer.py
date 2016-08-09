#!/usr/bin/python
# -*- coding: utf-8 -*-

try:
    from PyQt4.QtCore import Qt, QString, QObject, QUuid, QCryptographicHash
    from PyQt4.QtSql import QSqlDatabase, QSqlQuery, QSqlField, QSqlRecord, QSqlError
    from qgis.core import QgsMapLayer, QgsMapLayerRegistry, QGis, QgsVectorLayer, QgsRasterLayer, QgsDataSourceURI
	
except ImportError as e:
    print >> sys.stderr, 'E: Qt not installed.', e
    print >> sys.stderr, 'E: Exiting ...'
    sys.exit(1)

class SqlLayer():    
    
    def __init__(self, host, dbname, user, passw, port = 5432 ):
        self.host = host		
        self.port = port		
        self.dbname = dbname		
        self.user = user		
        self.passw = passw	
        self.typeGeoms = list()		
        self.typeRasters = list()
        self.schemaName = 'tmp_view_postgis_viewer'
        self.uidConnection = "PgSQL_LastQuery"
        self.connectToDb()

    def __del__(self):
        QSqlDatabase.removeDatabase(self.uidConnection)

    def createSqlLayer( self, sqlQuery, layerName = '' ):
        isVectorLayer, fieldName = self.findGeomColumns(sqlQuery)
        print 'I:geom columns=', fieldName.toLatin1().data(), ' isVectorLayer=', isVectorLayer
	
        if fieldName.isEmpty():
            print 'cannot find column with type geometry'
            return		
   
        if  len(layerName) == 0:
			layerName = 'query ' + QUuid.createUuid().toString()
        else:
            layers = QgsMapLayerRegistry.instance().mapLayersByName(layerName)
            print 'test layer count:', len(layers)	
            if len(layers) > 0:
                QgsMapLayerRegistry.instance().removeMapLayer( layers[0].id() );
			
        if  isVectorLayer == True:			
            uri = QgsDataSourceURI()
            uri.setConnection(self.host, self.port, self.dbname, self.user, self.passw)	
            uri.setDataSource("", self.appendIdColumn(sqlQuery, fieldName), fieldName, "", "id") #qgis.core.QgsDataSourceURI.setDataSource?4(QString, QString, QString, QString aSql=QString(), QString aKeyColumn=QString())    
            layer = QgsVectorLayer( uri.uri(), layerName, "postgres" ) 
        else:
            viewName = self.generateView(sqlQuery)
            connString = "PG: dbname=%s host=%s user=%s password=%s port=%s schema=%s table=%s" % ( self.dbname, self.host, self.user, self.passw, self.port, self.schemaName, viewName )
            print 'I:connString=', connString
            layer = QgsRasterLayer( connString, layerName )		
		
        if not layer.isValid() :
            print "Failed to load"	
            return 	
        
        QgsMapLayerRegistry.instance().addMapLayer( layer )	
	
    def generateView( self, sqlQuery ):
        name = 'TMP_' + QCryptographicHash.hash(sqlQuery.toUtf8(), QCryptographicHash.Md5).toHex()
        strQuery = QString('CREATE OR REPLACE VIEW '  + self.schemaName + '.' + name + ' AS ' + sqlQuery)
        self.execSql(strQuery)			
        return name
	
    def findGeomColumns(self, sqlQuery):	
        if len(self.typeGeoms) == 0 :
            self.loadDictTypes(self.sqlDatabase())
		
        query = self.execSql( "SELECT * FROM ( " + sqlQuery + " ) as sql_header LIMIT 0" )    
	
        for i in range(query.record().count()):
            typeId = QString.number(query.record().field(i).typeID())
            fieldName = query.record().field(i).name()
            if typeId in self.typeGeoms:
                return (True, fieldName)
            elif typeId in self.typeRasters:
                return (False, fieldName)

        return (False, QString(''))

	
    def loadDictTypes(self, db):
        query = self.execSql( 'SELECT oid, typname FROM pg_type' )
        while query.next():
            typname = query.value(1).toString().trimmed()
            oid = query.value(0).toString()
            if typname == 'geometry':
		        self.typeGeoms.append(oid)
            elif typname.startsWith('raster'):
		        self.typeRasters.append(oid)				
			
			
    def appendIdColumn(self, query, geomField):
        return '(select row_number() over(order by 1) id, q.' + geomField + ' from  ( ' + query.replace("\n", " ") +') as q)'		

    def connectToDb( self ):
        self.uidConnection = self.uidConnection + QUuid.createUuid().toString()
        d = QSqlDatabase.addDatabase( "QPSQL",  self.uidConnection)
        d.setHostName( self.host )
        d.setPort( int( self.port ) )
        d.setDatabaseName( self.dbname )
        d.setUserName( self.user )
        d.setPassword( self.passw )
        if not d.open():
            showError(None, 'error', 'error connect DB:  host:' + self.host + ' dbname:' + self.dbname + ' user:' + self.user + ' passw=' + self.passw )
		
        self.createScheme()
		
    def createScheme( self ):
        self.execSql('CREATE SCHEMA  ' + self.schemaName)
		
    def removeScheme( self ):
        print 'I:clean schema'
        self.execSql('DROP SCHEMA  ' + self.schemaName + ' CASCADE')		
			
    def execSql( self, strQuery ):
        strQuery = QString(strQuery)
        query = QSqlQuery( self.sqlDatabase() )	
        if query.exec_( strQuery ) != True:
            print "Failed execute ", strQuery.toLatin1().data(), ' error:' , query.lastError().databaseText().toLatin1().data()
			
        return query
			
    def sqlDatabase( self ):
        return QSqlDatabase.database(self.uidConnection)
		
    def showError(self, title, text):
        QMessageBox.critical(None, title, text,
        QMessageBox.Ok | QMessageBox.Default,
        QMessageBox.NoButton)
        print >> sys.stderr, 'E: Error. Exiting ...'
        print __doc__			