# -*- coding: utf-8 -*-
"""
/***************************************************************************
Name                 : RT Sql Layer - Query Manager
Description          : Load and save queries on a xml file
Date                 : 09/Apr/2010 
Copyright            : (c) 2010 by Giuseppe Sucameli (Faunalia)
Email                : brush.tyler@gmail.com 
 ***************************************************************************
Developed by Giuseppe Sucameli (brush.tyler@gmail.com) 
for Faunalia (http://www.faunalia.it) with funding from Regione Toscana - 
Sistema Informativo per la Gestione del Territorio e dell'Ambiente [RT-SIGTA]. 
For the project: "Sviluppo di prodotti software GIS open-source basati 
sui prodotti QuantumGIS e Postgis" (CIG 037728516E)
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

from PyQt4.QtCore import *
from PyQt4.QtGui import *

from PyQt4.QtXml import *

class QueryManager:

	class QueryItem():
		XML2ITEM = {
			'shortdescription' : 'description', 
			'description' : 'description', 
			'databasetype' : 'dbtype', 
			'databaseport' : 'dbport', 
			'databasehost' : 'dbhost', 
			'databasename' : 'dbname', 
			'sqlstatement' : 'query', 
			'sqluniquecolumn' : 'uniquecolumn',
			'sqlgeometrycolumn' : 'geomcolumn'
		}

		def __init__(self, description="", dbtype="", dbport="", dbhost="", dbname="", query="", uniquecolumn="", geomcolumn=""):
			self.description = description
			self.dbtype = dbtype
			self.dbport = dbport
			self.dbhost = dbhost
			self.dbname = dbname
			self.query = query
			self.uniquecolumn = uniquecolumn
			self.geomcolumn = geomcolumn

		@classmethod
		def newByDict(self, d):
			item = self()

			for k, v in d.iteritems():
				if not self.XML2ITEM.has_key( k ):
					continue

				name = self.XML2ITEM[ k ]
				setattr( item, name, v )

			return item

	@classmethod
	def save( self, filename, item = None ):
		if item == None:
			item = self.QueryItem()

		doc = QDomDocument()
		myInputFile = QFile( filename )
		xmlValid = False

		# If the file exists load it into a QDomDocument
		if myInputFile.exists():
			if not myInputFile.open( QIODevice.ReadOnly ):
				raise Exception( QCoreApplication.translate( "RT_SQL-Layer", "Unabled to open file [%1]" ).arg( filename ) )

			if myInputFile.size() > 0 and not myInputFile.atEnd():
				(xmlValid, errStr, errLine, errCol) = doc.setContent( myInputFile, False )
				if not xmlValid:
					raise Exception( QCoreApplication.translate( "RT_SQL-Layer", "Parse error at line %1, column %2" ).arg( errLine ).arg( errCol ) )

				root = doc.elementsByTagName("doc").at(0)

			myInputFile.close()

		if not xmlValid:
			instr = doc.createProcessingInstruction("xml","version=\"1.0\" encoding=\"UTF-8\" ")
			doc.appendChild(instr)

			root = doc.createElement("doc")

		doc.appendChild(root)

		queryTag = doc.createElement("query")
		root.appendChild(queryTag)

		tag = doc.createElement("shortdescription")
		queryTag.appendChild(tag)
		t = doc.createTextNode( item.description )
		tag.appendChild(t);

		tag = doc.createElement("description")
		queryTag.appendChild(tag)
		t = doc.createTextNode( item.description )
		tag.appendChild(t);

		tag = doc.createElement("databasetype")
		queryTag.appendChild(tag)
		t = doc.createTextNode( item.dbtype )
		tag.appendChild(t);

		tag = doc.createElement("databaseport")
		queryTag.appendChild(tag)
		t = doc.createTextNode( item.dbport )
		tag.appendChild(t);

		tag = doc.createElement("databasehost")
		queryTag.appendChild(tag)
		t = doc.createTextNode( item.dbhost )
		tag.appendChild(t);

		tag = doc.createElement("databasename")
		queryTag.appendChild(tag)
		t = doc.createTextNode( item.dbname )
		tag.appendChild(t);

		tag = doc.createElement("databaseusername")
		queryTag.appendChild(tag)

		tag = doc.createElement("databasepassword")
		queryTag.appendChild(tag)

		tag = doc.createElement("sqlstatement")
		queryTag.appendChild(tag)
		t = doc.createTextNode( item.query )
		tag.appendChild(t);

		tag = doc.createElement("sqlgeometrycolumn")
		queryTag.appendChild(tag)
		t = doc.createTextNode( item.geomcolumn )
		tag.appendChild(t);

		tag = doc.createElement("sqluniquecolumn")
		queryTag.appendChild(tag)
		t = doc.createTextNode( item.uniquecolumn )
		tag.appendChild(t);

		tag = doc.createElement("autoconnect")
		queryTag.appendChild(tag)
		t = doc.createTextNode("false")
		tag.appendChild(t);

		myOutputFile = QFile( filename )
		if not myOutputFile.open( QIODevice.WriteOnly ):
			raise Exception( QCoreApplication.translate( "RT_SQL-Layer", "Unabled to open file [%1]" ).arg( filename ) )

		xmlStream = QTextStream( myOutputFile )
		xmlStream.setCodec( QTextCodec.codecForName( "UTF-8" ) )
		xmlStream << doc.toString()

	@classmethod
	def load( self, filename, dbhost = "", dbname = "" ):
		queries = []

		# XXX There probably needs to be some more error checking, but works for now.
		# If the file exists load it into a QDomDocument
		myInputFile = QFile( filename )
		if not myInputFile.exists() or not myInputFile.open( QIODevice.ReadOnly ):
			raise Exception( QCoreApplication.translate( "RT_SQL-Layer", "Unabled to open file [%1]" ).arg( filename ) )

		if myInputFile.size() <= 0 or myInputFile.atEnd():
			return queries

		myXmlDoc = QDomDocument()
		(xmlValid, errStr, errLine, errCol) = myXmlDoc.setContent( myInputFile, False )
		myInputFile.close()

		if not xmlValid:
			#raise Exception( QCoreApplication.translate( "RT_SQL-Layer", "Parse error at line %1, column %2: %3" ).arg( errLine ).arg( errCol ).arg( errStr ) )
			raise Exception( QCoreApplication.translate( "RT_SQL-Layer", "Parse error at line %1, column %2" ).arg( errLine ).arg( errCol ) )


		#Loop through each child looking for a query tag
		myQueryCount = 0
		myNode = myXmlDoc.documentElement( ).firstChild( )
		while not myNode.isNull( ):
			if myNode.toElement( ).tagName( ) == "query":
				queryInfo = dict()

				myChildNodes = myNode.toElement( ).firstChild( )
				while not myChildNodes.isNull( ):
					myDataNode = myChildNodes.toElement( ).firstChild( )

					if not myDataNode.isNull( ):
						myDataNodeTagName = myChildNodes.toElement( ).tagName( )
						myDataNodeContent = myDataNode.toText( ).data( )
						queryInfo[ str(myDataNodeTagName) ] = myDataNodeContent

					myChildNodes = myChildNodes.nextSibling( )

				if queryInfo.has_key( "shortdescription" ): 
					# add the connection to the list only if its host and db are the same of the passed host and db
					if queryInfo.has_key( "databasehost" ) and not queryInfo["databasehost"].isEmpty():
						if queryInfo["databasehost"] != dbhost:
							myNode = myNode.nextSibling( )
							continue

					if queryInfo.has_key( "databasename" ) and not queryInfo["databasename"].isEmpty():
						if queryInfo["databasename"] != dbname:
							myNode = myNode.nextSibling( )
							continue

					qItem = self.QueryItem.newByDict( queryInfo )
					queries.append( qItem )

			myNode = myNode.nextSibling( )

		return queries

