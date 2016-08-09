# -*- coding: utf-8 -*-

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *

import postgis_utils
from DlgQueryBuilder import DlgQueryBuilder

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
  
  def initGui(self):
    # Create action that will start plugin configuration
    self.action = QAction(QIcon(":/icons/toolbar/action_sql_window.png"), "Query builder (RT Sql Layer)", self.iface.mainWindow())
    QObject.connect(self.action, SIGNAL("triggered()"), self.run)
  
    # Add toolbar button and menu item
    self.iface.addToolBarIcon(self.action)
  
  def unload(self):
    self.iface.removeToolBarIcon(self.action)
  
  def run(self):
    try:
      import psycopg2
    except ImportError, e:
      QMessageBox.information(self.iface.mainWindow(), "hey", "Couldn't import Python module 'psycopg2' for communication with PostgreSQL database. Without it you won't be able to run RT Sql Layer. Please install it.")
      return

    try:
      self.db = postgis_utils.GeoDB( self.host, int(self.port), self.dbname, self.user, self.passwd )
    except postgis_utils.DbError, e:
      self.statusBar.clearMessage()
      QMessageBox.critical(self, "error", "Couldn't connect to database:\n"+e.msg)
      return
    dlg = DlgQueryBuilder( self.iface.mainWindow(), self.db, self.iface )
    dlg.exec_()


