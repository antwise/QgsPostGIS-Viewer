# -*- coding: utf-8 -*-

from PyQt4.QtCore import Qt, QString
from PyQt4.QtGui import QDockWidget
from Legend import Legend

class ManagerPlugin:

  def __init__(self, iface, host, port, dbname, user, passwd):
    # Save reference to the QGIS interface
    self.iface = iface
  
  def initGui(self):	
    """ Create the map legend widget and associate to the canvas """
    legend = Legend( self.iface.mapCanvas(), self.iface.viewParamsView() )

    self.LegendDock = QDockWidget( legend.tr("Layers"), None )
    self.LegendDock.setWidget( legend )
    self.LegendDock.setContentsMargins ( 0, 0, 0, 0 )	
    self.iface.addDockWidget( Qt.RightDockWidgetArea, self.LegendDock )	

  def unload(self):
    self.iface.removeDockWidget( self.LegendDock )	


	
  