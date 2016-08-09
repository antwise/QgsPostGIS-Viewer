# -*- coding: utf-8 -*-

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.QtSql import QSqlDatabase, QSqlQuery, QSqlField, QSqlRecord

from qgis.core import *
from xml.dom import minidom

from ui.querydlg_ui import Ui_Dialog

import os
import resources

class ManagerPlugin:

  def __init__(self, iface, host, port, dbname, user, passwd):
    # Save reference to the QGIS interface
    self.iface = iface
    self.host = host 
    self.port = port
    self.dbname = dbname
    self.user = user
    self.passwd = passwd
    self.typeGeoms = list()
    self.systemWatcher = QFileSystemWatcher()
  
  def initGui(self):
    # Create action that will start plugin configuration
    self.action = QAction(QIcon(":/icons/last_query.png"), "PgAdmin query", self.iface.mainWindow())
    QObject.connect(self.action, SIGNAL("triggered()"), self.run)
    self.iface.addToolBarIcon(self.action)
	
    self.actionAuto = QAction(QIcon(":/icons/accelerator.png"), "Auto read pgAdminHistory", self.iface.mainWindow())
    self.actionAuto.setCheckable( True )
    QObject.connect(self.actionAuto, SIGNAL("toggled(bool)"), self.changeAutoMode)
    self.iface.addToolBarIcon(self.actionAuto)

    self.actionQuery = QAction(QIcon(":/icons/query.png"), "add query", self.iface.mainWindow())
    QObject.connect(self.actionQuery, SIGNAL("triggered()"), self.addSqlQuery)
    self.iface.addToolBarIcon(self.actionQuery)
	
    self.systemWatcher.addPath ( self.fileHistoryPgAdmin() )	
    self.actionAuto.setChecked( True )
	
  def unload(self):
    self.iface.removeToolBarIcon(self.action)
    self.iface.removeToolBarIcon(self.actionAuto)	
    self.iface.removeToolBarIcon(self.actionQuery)		
    self.changeAutoMode(false)
	
  def changeAutoMode(self, isAuto):
    if isAuto :
        QObject.connect(self.systemWatcher, SIGNAL("fileChanged(const QString&)"), self.run)
    else:
        QObject.disconnect(self.systemWatcher, SIGNAL("fileChanged(const QString&)"), self.run)    
		
  def addSqlQuery(self):
    dlg = QDialog()
    ui = Ui_Dialog()
    ui.setupUi(dlg)
    if not dlg.exec_() == QDialog.Accepted:
        return;
		
    sql = ui.textEdit.toPlainText () 
    print 'sql=', sql.toLatin1().data()
	
    self.iface.sqlLayerController().createSqlLayer(sql)
	
  def run(self):
    lastQuery = self.readLastQuery()
    print 'I:Last Query=', lastQuery.toLatin1().data()
	
    layerName = self.iface.tr('PgAdmin query')
    self.iface.sqlLayerController().createSqlLayer(lastQuery, layerName)
	
  def readLastQuery(self):
    xmldoc = minidom.parse( self.fileHistoryPgAdmin() )        
    itemlist = xmldoc.getElementsByTagName('histoquery')
    print 'T:count queries=', len(itemlist)
    if len(itemlist) == 0:
        return QString()
		
    return QString( itemlist[len(itemlist)-1].firstChild.data )

  def fileHistoryPgAdmin(self):
    return os.getenv('APPDATA') + '/postgresql/pgadmin_histoqueries.xml'
	