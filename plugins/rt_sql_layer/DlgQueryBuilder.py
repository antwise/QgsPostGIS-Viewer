# -*- coding: utf-8 -*-
"""
/***************************************************************************
Name                 : RT Sql Layer - Query Builder
Description          : Help to compose a query for loading a layer on canvas
Date                 : 08/Mar/10 
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

from qgis.core import *
from qgis.gui import *

from DatabaseModel import TableItem, SchemaItem, DatabaseModel
import postgis_utils
import psycopg2

from ui.DlgQueryBuilder_ui import Ui_Dialog
from DlgDbError import DlgDbError

from QueryParser import QueryParser
from QueryManager import QueryManager

class DlgQueryBuilder(QDialog, Ui_Dialog):
	
	def __init__(self, parent, db, iface):
		QDialog.__init__(self, parent)
		self.setupUi(self)

		self.db = db
		self.iface = iface

		self.dbModel = DatabaseModel(self,)
		self.dbModel.showOnlyReadableTables(True)
		self.tablesTree.setModel(self.dbModel)

		# setup signal-slot connections
		self.connect(self.buttonBox, SIGNAL("accepted()"), self.runQuery)

		self.connect(self.openFileBtn, SIGNAL("clicked()"), self.openQueriesFile)
		self.connect(self.queriesCombo, SIGNAL("currentIndexChanged(int)"), self.selectedQueryChanged)
		self.connect(self.loadQueryBtn, SIGNAL("clicked()"), self.loadSelectedQuery)

		self.connect(self.queryBrowser, SIGNAL("textChanged()"), self.queryChanged)
		self.connect(self.queryBrowser, SIGNAL("cursorPositionChanged()"), self.cursorPosChanged)
		self.connect(self.clearBtn, SIGNAL("clicked()"), self.clearBuilder)
		self.connect(self.getColumnsBtn, SIGNAL("clicked()"), self.fillColumnsCombo)

		self.connect(self.tablesTree.selectionModel(), SIGNAL("currentChanged(const QModelIndex&, const QModelIndex&)"), self.tableItemChanged)
		self.connect(self.tablesTree, SIGNAL("doubleClicked(const QModelIndex&)"), self.doubleClickTable)
		self.connect(self.tablesList, SIGNAL("itemSelectionChanged()"), self.refreshButtons)
		self.connect(self.outTableBtn, SIGNAL("clicked()"), self.clickOutTableBtn)
		self.connect(self.inTableBtn, SIGNAL("clicked()"), self.addTable)
		self.connect(self.joinBtn, SIGNAL("clicked()"), self.clickJoinBtn)
		self.connect(self.innerJoinBtn, SIGNAL("clicked()"), self.clickInnerJoinBtn)
		self.connect(self.outerJoinBtn, SIGNAL("clicked()"), self.clickOuterJoinBtn)

		self.connect(self.fieldsTree, SIGNAL("doubleClicked(const QModelIndex&)"), self.doubleClickField)
		self.connect(self.fieldsTree, SIGNAL("itemSelectionChanged()"), self.refreshButtons)
		self.connect(self.fieldsList, SIGNAL("itemSelectionChanged()"), self.refreshButtons)
		self.connect(self.outFieldBtn, SIGNAL("clicked()"), self.clickOutFieldBtn)
		self.connect(self.inFieldBtn, SIGNAL("clicked()"), self.doubleClickField)

		self.connect(self.fieldsCondTree, SIGNAL("doubleClicked(const QModelIndex&)"), self.doubleClickCondField)
		self.connect(self.eqBtn, SIGNAL("clicked()"), self.clickOpEq)
		self.connect(self.neqBtn, SIGNAL("clicked()"), self.clickOpNEq)
		self.connect(self.gtBtn, SIGNAL("clicked()"), self.clickOpGt)
		self.connect(self.gteBtn, SIGNAL("clicked()"), self.clickOpGtE)
		self.connect(self.ltBtn, SIGNAL("clicked()"), self.clickOpLt)
		self.connect(self.lteBtn, SIGNAL("clicked()"), self.clickOpLtE)
		self.connect(self.inBtn, SIGNAL("clicked()"), self.clickOpIn)
		self.connect(self.ninBtn, SIGNAL("clicked()"), self.clickOpNIn)
		self.connect(self.andBtn, SIGNAL("clicked()"), self.clickOpAnd)
		self.connect(self.orBtn, SIGNAL("clicked()"), self.clickOpOr)
		self.connect(self.notBtn, SIGNAL("clicked()"), self.clickOpNot)
		self.connect(self.likeBtn, SIGNAL("clicked()"), self.clickOpLike)
		self.connect(self.ilikeBtn, SIGNAL("clicked()"), self.clickOpILike)
		self.connect(self.percBtn, SIGNAL("clicked()"), self.clickOpPerc)
		self.connect(self.inValueBtn, SIGNAL("clicked()"), self.addCondValue)

		self.init()
		self.refreshTables()

	def lastUsedFile(self):
		settings = QSettings()
		filename = settings.value( "/openGeo_RT/lastUsedFile", QVariant("") ).toString()
		if not QFile(filename).exists():
			filename = ""

		return QString(filename)

	def setLastUsedFile(self, filename):
		settings = QSettings()
		settings.setValue( "/openGeo_RT/lastUsedFile", QVariant(filename) )

	def saveQuery(self):
		if not self.saveQueryCheck.isChecked():
			return True

		filename = self.fileEdit.text()		
		if filename.isEmpty():
			filename = QFileDialog.getSaveFileName(self, self.tr( "Select where you want to save the query" ), QString(), self.tr( "XML file (*.xml)" ))
			if filename.isEmpty():
				return False

			if not filename.toUpper().endsWith(".XML"):
				filename.append(".xml")
			self.setLastUsedFile(filename)

		qItem = QueryManager.QueryItem()
		qItem.description = self.queryNameEdit.text()
		qItem.dbtype = "POSTGRES"
		qItem.dbport = str(self.db.port)
		qItem.dbhost = self.db.host
		qItem.dbname = self.db.dbname
		qItem.query = self.queryBrowser.toPlainText()
		qItem.uniquecolumn = self.uniqueCombo.currentText()
		qItem.geomcolumn = self.geomCombo.currentText()

		try:
			QueryManager.save( filename, qItem )
		except Exception, e:
			QMessageBox.critical( self, self.tr( "Error" ), str(e).replace("\n", "<br>") )
			return False

		return True

	def loadQueriesFromFile(self, filename):
		self.queriesCombo.clear()
		self.queriesCombo.setCurrentIndex(-1)

		if filename.isEmpty():
			return

		try:
			queries = QueryManager.load( filename, self.db.host, self.db.dbname )
		except Exception, e:
			QMessageBox.critical( self, self.tr( "Parse error" ), str(e).replace("\n", "<br>") )
			return

		self.loadedQueries = queries
		for q in queries:
			self.queriesCombo.addItem( q.description )

	def openQueriesFile(self):
		lastUsedFile = self.lastUsedFile()
		inputFile = QFileDialog.getOpenFileName(self, self.tr( "Select the file containing queries" ), lastUsedFile, self.tr( "XML file (*.xml)" ))
		if inputFile.isEmpty():
			return
		self.setLastUsedFile(inputFile)
		self.fileEdit.setText(inputFile)

		if QFile( inputFile ).exists():
			self.loadQueriesFromFile(inputFile)

	def selectedQueryChanged(self):
		self.loadQueryBtn.setEnabled( self.queriesCombo.currentIndex() >= 0 )

	def loadSelectedQuery(self):
		index = self.queriesCombo.currentIndex()
		if index < 0:
			return

		self.clearBuilder()
		qItem = self.loadedQueries[index]

		self.queryBrowser.setPlainText( qItem.query )
		self.geomCombo.setEditText( qItem.geomcolumn )
		self.uniqueCombo.setEditText( qItem.uniquecolumn )

	def sanitizeQuery(self, query):
		# check that query starts with SELECT
		regex = QRegExp( '^SELECT' + QueryParser.escape(' '), Qt.CaseInsensitive )
		if not query.contains(regex):
			query = "SELECT " + query

		# remove all comments and truncate the query to ;
		query = QueryParser(query, sanitize=True).query
		return query + '\n'

	def runQuery(self):
		uniqueFieldName = self.uniqueCombo.currentText()
		geomFieldName = self.geomCombo.currentText()

		if geomFieldName.isEmpty() or uniqueFieldName.isEmpty():
			QMessageBox.warning(self, self.tr( "Cannot execute the query" ), self.tr( "You must fill the required fields: \ngeometry column - column with unique integer values" ) )
			return

		QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))

		query = self.queryBrowser.toPlainText()
		query = self.sanitizeQuery(query)

		# make sure there are no duplicated column names in the result
		try:
			self.getRetColumns( query )

		except postgis_utils.DbError, e:
			QApplication.restoreOverrideCursor()
			DlgDbError.showError(e, self)
			return

		except Exception, e:
			QApplication.restoreOverrideCursor()
			QErrorMessage(self).showMessage( str(e).replace("\n", "<br>") )
			return

		# get a new layer name
		names = []
		for layer in QgsMapLayerRegistry.instance().mapLayers().values():
			names.append( layer.name() )

		index = 1
		newLayerName = "Query layer %s"
		while names.count( newLayerName % index ) > 0:
			index += 1
		newLayerName = newLayerName % index

		# create the layer			
		uri = QgsDataSourceURI()
		uri.setConnection(self.db.host, str(self.db.port), self.db.dbname, self.db.user, self.db.passwd)
		uri.setDataSource("", "(" + str(query).replace("\n", "") + ")", geomFieldName, "", uniqueFieldName)
		layer = QgsVectorLayer( uri.uri(), newLayerName, "postgres" ) 
		if layer.isValid() :
			QgsMapLayerRegistry.instance().addMapLayer( layer )	

		QApplication.restoreOverrideCursor()

		if layer.isValid():
			self.saveQuery()
			self.accept()

	def fillColumnsCombo(self):
		QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))

		# retrieve the columns in the query result
		query = self.queryBrowser.toPlainText()
		try:
			retcols = self.getRetColumns( query )

		except postgis_utils.DbError, e:
			QApplication.restoreOverrideCursor()
			DlgDbError.showError(e, self)
			return

		except Exception, e:
			QApplication.restoreOverrideCursor()
			QErrorMessage(self).showMessage( str(e).replace("\n", "<br>") )
			return

		# retrieve the type name of the columns by the type oid
		typeOids = list()
		for f in retcols:
			ftype = str( f[1] )
			if typeOids.count( ftype ) <= 0:
				typeOids.append( ftype )
		typeOids = ",".join( typeOids )

		c = self.db.con.cursor()
		self.db._exec_sql(c, "SELECT oid, typname FROM pg_type WHERE oid IN (%s)" % typeOids )

		types = dict()
		for oid, typename in c.fetchall():
			types[oid] = typename

		c.close()

		# fill both the geometry and the unique combo
		uniqueCols = list()
		geomCols = list()
		for f in retcols:
			ftypename = types[ f[1] ]

			if ftypename == "oid" or ftypename == "serial" or ftypename == "int4":
				uniqueCols.append( f[0] )
			if ftypename == "geometry":
				geomCols.append( f[0] )


		uniqueCols.sort()
		self.uniqueCombo.clear()
		self.uniqueCombo.addItems( uniqueCols )

		geomCols.sort()
		self.geomCombo.clear()
		self.geomCombo.addItems( geomCols )

		QApplication.restoreOverrideCursor()

	def getRetColumns(self, query):
		query = self.sanitizeQuery(query)

		# get a new alias
		finded = False
		sp = QueryParser.escape(' ')
		while not finded:
			alias = self.newTableAlias()
			escaped = sp + '("?)' + QRegExp.escape(alias) + '\\1' + sp
			regex = QRegExp( escaped , Qt.CaseInsensitive )
			finded = not query.contains(regex)
		self.lastAliasIndex -= 1

		# check if there are fields with duplicated names in the result 
		newQuery = "SELECT * FROM ( %s ) AS %s LIMIT 0" % ( unicode(query), self.db._quote(alias) )
		try:
			c = self.db.con.cursor()
			self.db._exec_sql(c, unicode(newQuery))
		except Exception, e:
			# if an error occurs could be a syntax error, 
			# so exec the original query to show the right error message
			c = self.db.con.cursor()
			self.db._exec_sql(c, unicode(query))
			c.close()

			# XXX this code is reached only if newQuery throw an exception and the original doesn't do it
			# we throw the previuos exception
			raise e

		retfields = dict()
		for fld in c.description:
			# make sure there are no duplicated fields
			if retfields.has_key( fld[0] ) > 0:
				raise Exception( self.tr( "Columns with duplicated names are not allowed in the result. \nUse an alias to make sure there is only one '%1' column." ).arg( fld[0] ) )

			retfields[fld[0]] = fld

		c.close()

		return retfields.values()

	def cursorPosChanged(self):
		cursor = self.queryBrowser.textCursor()
		query = self.queryBrowser.toPlainText()

		# user can only select the cursor before the SELECT statement
		if cursor.position() < 7:
			endPos = min(query.size(), 7)
			if cursor.anchor() != cursor.position():
				startPos = cursor.anchor()
				if cursor.anchor() < 7:
					startPos = endPos
				else:
					endPos = 0

				cursor.setPosition(startPos)
				cursor.setPosition(endPos, QTextCursor.KeepAnchor)
			else:
				cursor.setPosition(endPos)

			self.queryBrowser.setTextCursor(cursor)

	def queryChanged(self):
		query = self.queryBrowser.toPlainText()

		regex = QRegExp( '^SELECT' + QueryParser.escape(' '), Qt.CaseInsensitive )
		if not query.contains(regex):
			query = "SELECT " + query
			self.queryBrowser.setPlainText(query)
			self.queryBrowser.moveCursor(QTextCursor.End)

		self.parser = QueryParser(query, parseNow=False)

	def refreshTables(self):
		model = self.tablesTree.model()
		model.loadFromDb(self.db)
		model.reset()

		# only expand when there are not too many tables
		if model.tree.tableCount < 20:
			self.tablesTree.expandAll()
		
		self.tablesTree.currentItem = None
		self.refreshButtons()

	def refreshButtons(self):
		self.enableTableButtons()
		self.enableFieldButtons()

	def enableTableButtons(self):
		treeSel = self.tablesTree.currentItem != None
		listCount = self.tablesList.count() > 0
		listSel = len(self.tablesList.selectedItems()) > 0

		self.joinBtn.setEnabled(treeSel and listCount)
		self.innerJoinBtn.setEnabled(treeSel and listCount)
		self.outerJoinBtn.setEnabled(treeSel and listCount)
		self.inTableBtn.setEnabled(treeSel)
		self.outTableBtn.setEnabled(listSel)

	def enableFieldButtons(self):
		selItems = self.fieldsTree.selectedItems()
		treeSel = len(selItems) > 0 and selItems[0].parent() != None
		listSel = len(self.fieldsList.selectedItems()) > 0

		self.inFieldBtn.setEnabled(treeSel)
		self.outFieldBtn.setEnabled(listSel)

	def clearBuilder(self):
		self.tablesList.clear()
		self.fieldsTree.clear()
		self.fieldsList.clear()
		self.fieldsCondTree.clear()
		self.valueEdit.clear()

		query = "SELECT * FROM"
		self.queryBrowser.setPlainText(query)
		self.parser = QueryParser(query, parseNow=False)

		self.geomCombo.clear()
		self.geomCombo.clearEditText()
		self.uniqueCombo.clearEditText()
		self.toolBox.setCurrentIndex(0)

	def init(self):
		self.tablesTree.currentItem = None
		self.clearBuilder()

		filename = self.lastUsedFile()
		self.fileEdit.setText( filename )
		self.loadQueriesFromFile( filename )
		self.selectedQueryChanged()

		self.refreshButtons()

	def tableItemChanged(self, curr, prev):
		item = curr.internalPointer()
		if not isinstance(item, TableItem):
			self.tablesTree.currentItem = None
		else:
			self.tablesTree.currentItem = (item.schema().name, item.name)
		self.refreshButtons()

	def clickOutTableBtn(self):
 		if self.tablesList.count() == 0:
			return

		selItems = self.tablesList.selectedItems()
		if len(selItems) == 0:
			return

		self.delTable(selItems[0])

	def delTable(self, item):
		# remove table from the selected list
		row = self.tablesList.row(item)
		item = self.tablesList.takeItem(row)

		if not self.parse():
			return

		fromIndex = self.parser.indexOfPart( "FROM" )
		if fromIndex < 0:
			return

		query = self.queryBrowser.toPlainText()

		# remove the table from query browser
		tableName = QRegExp.escape(item.name(True))
		joinRegex = '(?:\\s*,\\s*|' + QueryParser.escape( [' JOIN ', ' INNER JOIN ', ' OUTER JOIN '] ) + ')?'

		regex = QRegExp( tableName + joinRegex + '|' + joinRegex + tableName, Qt.CaseInsensitive )
		query = query.remove(regex)

		self.queryBrowser.setPlainText( query )

		self.refreshButtons()

		# remove the table's fields from both the fields trees
		tItem = self.fieldsTree.findItems(item.text(), Qt.MatchFixedString)[0]
		index = self.fieldsTree.indexOfTopLevelItem(tItem)
		self.fieldsTree.takeTopLevelItem(index)

		tCondItem = self.fieldsCondTree.findItems(item.text(), Qt.MatchFixedString)[0]
		index = self.fieldsCondTree.indexOfTopLevelItem(tCondItem)
		self.fieldsCondTree.takeTopLevelItem(index)

		# now there is a button to fill the combos
		"""
		# remove the geometry and unique fields from the combos
		if not self.geomUniqueDict.has_key( item.name(True) ):
			return

		for geom in self.geomUniqueDict[ item.name(True) ] ['geom']:
			index = self.geomCombo.findText( geom )
			if index != -1:
				fieldsNum = self.geomCombo.itemData( index ).toInt()[0]
				if fieldsNum - 1 > 0:
					self.geomCombo.setItemData( index, QVariant(fieldsNum - 1) )
				else:
					self.geomCombo.removeItem( index )

		for unique in self.geomUniqueDict[ item.name(True) ] ['unique']:
			index = self.uniqueCombo.findText( unique )
			if index != -1:
				fieldsNum = self.uniqueCombo.itemData( index ).toInt()[0]
				if fieldsNum - 1 > 0:
					self.uniqueCombo.setItemData( index, QVariant(fieldsNum - 1) )
				else:
					self.uniqueCombo.removeItem( index )
		"""

		# remove the returned fields
		indexes = range(self.fieldsList.count())
		indexes.reverse()
		for i in indexes:
			item = self.fieldsList.item(i)
			if item.table == tItem.alias:
				self.delField(item)


	def doubleClickTable(self, modelIndex):
		self.addTable()

	def clickJoinBtn(self):
		self.addTable('JOIN')

	def clickInnerJoinBtn(self):
		self.addTable('INNER JOIN')

	def clickOuterJoinBtn(self):
		self.addTable('OUTER JOIN')

	def addTable(self, joinType = None):
		item = self.tablesTree.currentItem
		if item == None: return

		if not self.parse():
			return

		query = self.queryBrowser.toPlainText()

		finded = False
		sp = QueryParser.escape(' ')
		while not finded:
			alias = self.newTableAlias()
			escaped = sp + '("?)' + QRegExp.escape(alias) + '\\1' + sp
			regex = QRegExp( escaped, Qt.CaseInsensitive )
			finded = not query.contains(regex)

		# add the table to the selected tables list
		item = ListTableItem(item[0], item[1], alias)
		self.tablesList.addItem(item)

		# add the selected table to the query browser
		tableJoined = " " + item.name(True)

		fromIndex = self.parser.indexOfPart( "FROM" )
		allParts = self.parser.parts
		if fromIndex < 0:
			# add the FROM statement to the SELECT one
			selectIndex = self.parser.indexOfPart( "SELECT" )
			if selectIndex < 0:
				raise NotSelectQuery()

			allParts[selectIndex] += " FROM" + tableJoined
		else:
			# if there is at least one table after the FROM clause 
			# we have to add a , or the JOIN type
			fromPart = self.parser.parts[fromIndex]
			tablesParser = QueryParser(fromPart.mid(5), ',', sanitize=True)
			if not tablesParser.parts.isEmpty():
				if joinType == None:
					tableJoined.prepend(",")
				else:
					tableJoined.prepend(" " + joinType)

			allParts[fromIndex] += tableJoined

		self.queryBrowser.setPlainText( allParts.join(" ") )

		# add table's fields to the both fields trees
		tItem = TreeTableItem(item.schema, item.table, item.alias)
		self.fieldsTree.addTopLevelItem(tItem)

		tCondItem = TreeTableItem(item.schema, item.table, item.alias)
		self.fieldsCondTree.addTopLevelItem(tCondItem)

		fields = self.db.get_table_fields(item.table, item.schema)
		for f in fields:
			tChild = TreeFieldItem(item.alias, f.name)
			tItem.addChild(tChild)

			tCondChild = TreeFieldItem(item.alias, f.name)
			tCondItem.addChild(tCondChild)

		# now there is a button to fill the combos
		"""
		# add geometry and unique fields
		if not hasattr( self, 'geomUniqueDict' ):
			self.geomUniqueDict = dict()

		if not self.geomUniqueDict.has_key( item.name(True) ):
			self.geomUniqueDict[ item.name(True) ] = self.getGeomAndUniqueFields( item )

		for geom in self.geomUniqueDict[ item.name(True) ] ['geom']:
			index = self.geomCombo.findText( geom )
			if index != -1:
				fieldsNum = self.geomCombo.itemData( index ).toInt()[0]
				self.geomCombo.setItemData( index, QVariant(fieldsNum + 1) )
			else:
				self.geomCombo.addItem( geom, QVariant(1) )

		for unique in self.geomUniqueDict[ item.name(True) ] ['unique']:
			index = self.uniqueCombo.findText( unique )
			if index != -1:
				fieldsNum = self.uniqueCombo.itemData( index ).toInt()[0]
				self.uniqueCombo.setItemData( index, QVariant(fieldsNum + 1) )
			else:
				self.uniqueCombo.addItem( unique, QVariant(1) )
		"""

		# only expand when there are not too many items
		if self.fieldsTree.topLevelItemCount() < 2:
			self.fieldsTree.expandItem(tItem)
			self.fieldsCondTree.expandItem(tCondItem)
		else:
			self.fieldsTree.collapseAll()
			self.fieldsCondTree.collapseAll()

		self.refreshButtons()

	def getGeomAndUniqueFields(self, item):
		ret = { 'geom': [], 'unique': [] }

		fields = self.db.get_table_fields(item.table, item.schema)
		constraints = self.db.get_table_constraints(item.table, item.schema)
		uniqueIndexes = self.db.get_table_unique_indexes(item.table, item.schema)
		for f in fields:
			# add geometry fields to the geom combo
			if f.data_type == "geometry":
				ret['geom'].append(f.name)

			# add both the serial and int4 fields with unique index
			for u in uniqueIndexes:
				if ( f.data_type == "oid" or f.data_type == "serial" or f.data_type == "int4" ) and \
						len(u.columns) == 1 and f.num in u.columns:
					ret['unique'].append(f.name)
					break

			# add pk and unique fields to the unique combo
			for c in constraints:
				if ( c.con_type == postgis_utils.TableConstraint.TypePrimaryKey or \
						c.con_type == postgis_utils.TableConstraint.TypeUnique ) and \
						len(c.keys) == 1 and f.num in c.keys:
					ret['unique'].append(f.name)
					break

		return ret

	def clickOutFieldBtn(self):
 		if self.fieldsList.count() == 0:
			return

		selItems = self.fieldsList.selectedItems()
		if len(selItems) == 0:
			return

		self.delField(selItems[0])

	def delField(self, item):
		if not self.parse():
			return

		# remove the field from selected fields list
		row = self.fieldsList.row(item)
		self.fieldsList.takeItem(row)

		# remove the field from query browser
		query = self.queryBrowser.toPlainText()
		regex = QRegExp.escape(item.name(True))
		joinRegex = '(?:,\\s*)?'

		regex = QRegExp( regex + joinRegex + '|' + joinRegex + regex, Qt.CaseInsensitive )
		query = query.remove(regex)

		# check if there are other fields
		parser = QueryParser( query )
		selectIndex = parser.indexOfPart( "SELECT" )
		if selectIndex < 0:
			raise 

		selectPart = parser.parts[ selectIndex ]
		if selectPart.compare( "SELECT", Qt.CaseInsensitive ) == 0:
			regex = QRegExp( '^SELECT' + QueryParser.escape(' '), Qt.CaseInsensitive )
			query = query.replace(regex, 'SELECT * ')

		self.queryBrowser.setPlainText(query)

		self.refreshButtons()

	def doubleClickField(self):
		self.addField()

	def addField(self):
		selItems = self.fieldsTree.selectedItems()
		if len(selItems) == 0: return
		if selItems[0].parent() == None: return

		if not self.parse():
			return

		# add field to the selected fields list
		item = ListFieldItem(selItems[0].table, selItems[0].field)
		self.fieldsList.addItem(item)

		# add the field to the query browser
		fieldReturned = " " + item.name(True)

		selectIndex = self.parser.indexOfPart( "SELECT" )
		if selectIndex < 0:
			raise NotSelectQuery()

		allParts = self.parser.parts

		selectPart = self.parser.parts[selectIndex]
		fieldsParser = QueryParser(selectPart.mid(7), ',', sanitize=True)
		# if there is at least one field after the SELECT clause 
		# and if this field is not a '*', we have to add a ','
		if not fieldsParser.parts.isEmpty():
			if fieldsParser.parts.count() == 1 and fieldsParser.parts[0] == "*":
				allParts[selectIndex] = "SELECT"
			else:
				fieldReturned.prepend(",")
		allParts[selectIndex] += fieldReturned

		self.queryBrowser.setPlainText( allParts.join(" ") )

		self.refreshButtons()

	def doubleClickCondField(self, modelIndex):
		self.addCondField()

	def addCondField(self):
		selItems = self.fieldsCondTree.selectedItems()
		if len(selItems) == 0: return
		if selItems[0].parent() == None: return

		if not self.parse():
			return

		# add the field to the query browser
		field = " " + selItems[0].name(True)

		cursor = self.queryBrowser.textCursor()

		whereIndex = self.parser.indexOfPart( "WHERE" )
		allParts = self.parser.parts
		if whereIndex < 0:
			# add the WHERE statement to the FROM one or, 
			# if not present, to the SELECT one
			index = self.parser.indexOfPart( "FROM" )
			if index < 0:
				index = self.parser.indexOfPart( "SELECT" )
				if index < 0:
					raise NotSelectQuery()

			allParts[index] += " WHERE"
			self.queryBrowser.setPlainText( allParts.join(" ") )

			pos = 0
			for i in range(index + 1):
				pos += allParts[i].length()
			cursor.setPosition(pos)
		else:
			pos = 0
			for i in range(whereIndex):
				pos += allParts[i].length()

			if cursor.position() <= pos + 5:
				cursor.setPosition(pos + 5)

		self.adjustCursorPosition(cursor)
		self.queryBrowser.setTextCursor(cursor)
		self.queryBrowser.insertPlainText(field)

		self.refreshButtons()

	def addCondValue(self):
		value = " " + self.quotedValue(self.valueEdit.text()) + " "

		cursor = self.queryBrowser.textCursor()

		if not self.parse():
			return

		whereIndex = self.parser.indexOfPart( "WHERE" )
		allParts = self.parser.parts
		if whereIndex < 0:
			# add the WHERE statement to the FROM one or, 
			# if not present, to the SELECT one
			index = self.parser.indexOfPart( "FROM" )
			if index < 0:
				index = self.parser.indexOfPart( "SELECT" )
				if index < 0:
					raise NotSelectQuery()

			allParts[index] += " WHERE"
			self.queryBrowser.setPlainText( allParts.join(" ") )

			pos = 0
			for i in range(index + 1):
				pos += allParts[i].length()
			cursor.setPosition(pos)
		else:
			pos = 0
			for i in range(whereIndex):
				pos += allParts[i].length()

			if cursor.position() <= pos + 5:
				cursor.setPosition(pos + 5)

		self.adjustCursorPosition(cursor)
		self.queryBrowser.setTextCursor(cursor)
		self.queryBrowser.insertPlainText(value)

		self.refreshButtons()

	def adjustCursorPosition(self, cursor):
		pos = cursor.position()
		cursor.movePosition(QTextCursor.StartOfWord)
		if cursor.position() == pos:
			cursor.movePosition(QTextCursor.PreviousCharacter)
		else:
			cursor.movePosition(QTextCursor.EndOfWord)

	def clickOpEq(self):
		self.queryBrowser.insertPlainText(" = ")

	def clickOpNEq(self):
		self.queryBrowser.insertPlainText(" != ")

	def clickOpGt(self):
		self.queryBrowser.insertPlainText(" > ")

	def clickOpLt(self):
		self.queryBrowser.insertPlainText(" < ")

	def clickOpGtE(self):
		self.queryBrowser.insertPlainText(" >= ")

	def clickOpLtE(self):
		self.queryBrowser.insertPlainText(" <= ")

	def clickOpIn(self):
		self.queryBrowser.insertPlainText(" IN ")

	def clickOpNIn(self):
		self.queryBrowser.insertPlainText(" NOT IN ")

	def clickOpAnd(self):
		self.queryBrowser.insertPlainText(" AND ")

	def clickOpOr(self):
		self.queryBrowser.insertPlainText(" OR ")

	def clickOpNot(self):
		self.queryBrowser.insertPlainText(" NOT ")

	def clickOpLike(self):
		self.queryBrowser.insertPlainText(" LIKE ")

	def clickOpILike(self):
		self.queryBrowser.insertPlainText(" ILIKE ")

	def clickOpPerc(self):
		self.queryBrowser.insertPlainText("%")

	def newTableAlias(self):
		if not hasattr(self, 'lastAliasIndex'):
			self.lastAliasIndex = 0
		else:
			self.lastAliasIndex += 1
		return "t_" + str( self.lastAliasIndex )

	@staticmethod
	def quotedIdentifier(ident):
		ident = QString(ident)
		ident = ident.replace( '"', '""' )
		return ident.prepend( '"' ).append( '"' )

	@staticmethod
	def quotedValue(value):
		value = QString(value)
		if value.isNull():
			return "NULL"

		value.replace( "'", "''" )
		return value.prepend( "'" ).append( "'" )

	def parse(self):
		if not self.parser.parse():
			QMessageBox.warning( self, self.tr( "Invalid query" ), self.tr( "Correct the opening/closing of quotes and parenthesys before continuing." ) )
			return False
		return True


class NotSelectQuery (Exception):
	def __init__(self):
		msg = self.tr( "Error: The query doesn't start with SELECT statement" )
		Exception.__init__( self, msg )


class ListTableItem(QListWidgetItem):
	def __init__(self, schema, table, alias = None):
		self.schema = schema
		self.table = table
		self.alias = alias

		QListWidgetItem.__init__(self)
		self.setText(self.name())

	def name(self, quoted=False):
		schema = self.schema if not quoted else DlgQueryBuilder.quotedIdentifier(self.schema)
		table = self.table if not quoted else DlgQueryBuilder.quotedIdentifier(self.table)

		s = schema + "." + table
		if self.alias != None:
			alias = self.alias if not quoted else DlgQueryBuilder.quotedIdentifier(self.alias)
			s += " AS " + alias

		return s


class ListFieldItem(QListWidgetItem):
	def __init__(self, table, field):
		self.table = table
		self.field = field

		QListWidgetItem.__init__(self)
		self.setText(self.name())

	def name(self, quoted=False):
		table = self.table if not quoted else DlgQueryBuilder.quotedIdentifier(self.table)
		field = self.field if not quoted else DlgQueryBuilder.quotedIdentifier(self.field)
		return table + "." + field


class TreeTableItem(QTreeWidgetItem):
	def __init__(self, schema, table, alias = None):
		self.schema = schema
		self.table = table
		self.alias = alias

		QListWidgetItem.__init__(self)
		self.setText(0, self.name())

	def name(self, quoted=False):
		schema = self.schema if not quoted else DlgQueryBuilder.quotedIdentifier(self.schema)
		table = self.table if not quoted else DlgQueryBuilder.quotedIdentifier(self.table)

		s = schema + "." + table
		if self.alias != None:
			alias = self.alias if not quoted else DlgQueryBuilder.quotedIdentifier(self.alias)
			s += " AS " + alias

		return s


class TreeFieldItem(QTreeWidgetItem):
	def __init__(self, table, field):
		self.table = table
		self.field = field

		QListWidgetItem.__init__(self)
		self.setText(0, self.field)

	def name(self, quoted=False):
		table = self.table if not quoted else DlgQueryBuilder.quotedIdentifier(self.table)
		field = self.field if not quoted else DlgQueryBuilder.quotedIdentifier(self.field)
		return table + "." + field

