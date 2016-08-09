#!/usr/bin/python
# -*- coding: utf-8 -*-

import os, sys, math, imp, fileinput, re
import getpass, pickle # import stuff for ipc

try:
    from PyQt4.QtGui import QApplication
    from PyQt4.QtCore import SIGNAL, Qt, QString, QSharedMemory, QIODevice, QObject
    from PyQt4.QtNetwork import QLocalServer, QLocalSocket

except ImportError as e:
    print >> sys.stderr, 'E: Qt not installed.', e
    print >> sys.stderr, 'E: Exiting ...'
    sys.exit(1)

class SingletonApp(QApplication):
    
    timeout = 1000
    
    def __init__(self, argv, application_id=None):
        QApplication.__init__(self, argv)
        
        self.socket_filename = unicode(os.path.expanduser("~/.ipc_%s" % self.generate_ipc_id()) )
        self.shared_mem = QSharedMemory()
        self.shared_mem.setKey(self.socket_filename)

        if self.shared_mem.attach():
            self.is_running = True
            return
        
        self.is_running = False
        if not self.shared_mem.create(1):
            print >>sys.stderr, "Unable to create single instance"
            return
        # start local server
        self.server = QLocalServer(self)
        # connect signal for incoming connections
        self.connect(self.server, SIGNAL("newConnection()"), self.receive_message)
        # if socket file exists, delete it
        if os.path.exists(self.socket_filename):
            os.remove(self.socket_filename)
        # listen
        self.server.listen(self.socket_filename)

    def __del__(self):
        self.shared_mem.detach()
        if not self.is_running:
            if os.path.exists(self.socket_filename):
                os.remove(self.socket_filename)
       
    def generate_ipc_id(self, channel=None):
        if channel is None:
            channel = os.path.basename(sys.argv[0])
        return "%s_%s" % (channel, getpass.getuser())

    def send_message(self, message):
        if not self.is_running:
            raise Exception("Client cannot connect to IPC server. Not running.")
        socket = QLocalSocket(self)
        socket.connectToServer(self.socket_filename, QIODevice.WriteOnly)
        if not socket.waitForConnected(self.timeout):
            raise Exception(str(socket.errorString()))
        socket.write(pickle.dumps(message))
        if not socket.waitForBytesWritten(self.timeout):
            raise Exception(str(socket.errorString()))
        socket.disconnectFromServer()
        
    def receive_message(self):
        socket = self.server.nextPendingConnection()
        if not socket.waitForReadyRead(self.timeout):
            print >>sys.stderr, socket.errorString()
            return
        byte_array = socket.readAll()
        self.handle_new_message(pickle.loads(str(byte_array)))

    def handle_new_message(self, message):
        self.emit( SIGNAL("message"), message )
