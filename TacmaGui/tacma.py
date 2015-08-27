#!/usr/bin/env python

import sys
from PyQt5 import QtWidgets, QtCore, QtGui
from mtab import MainWindowTable
import tacmaopt
from wfile import TacmaData
import bproc

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, fn):
        super(MainWindow, self).__init__()
        self.data = TacmaData(fn)
        self.setUi()

        #autosave and save at exit
        if tacmaopt.opt.autosave > 0:
            self.timer_autosave = QtCore.QTimer(self)
            self.timer_autosave.timeout.connect(self._autosave)
            self.timer_autosave.start(tacmaopt.opt.autosave * 60000)
        if tacmaopt.opt.backup_autosave > 0:
            self.timer_bautosave = QtCore.QTimer(self)
            self.timer_bautosave.timeout.connect(self._bautosave)
            self.timer_bautosave.start(tacmaopt.opt.backup_autosave * 60000)
        import atexit
        atexit.register(self._autosave)
        atexit.register(tacmaopt.opt.write)


    def setUi(self):
        self.setWindowTitle(tacmaopt.opt.title())
        #self.setWindowIcon(QtGui.QIcon('misc/mainwin.png'))
        self.setWindowIcon(bproc.get_icon('tacma'))
        self.resize(tacmaopt.opt.Hx, tacmaopt.opt.Hy)
        self.move(tacmaopt.opt.x0, tacmaopt.opt.y0)

        #menu
        menubar = self.menuBar()
        filemenu = menubar.addMenu('&File')
        exit_action = QtWidgets.QAction('E&xit', self)
        exit_action.triggered.connect(QtWidgets.qApp.quit)
        filemenu.addAction(exit_action)

        #central widget
        self.tab = MainWindowTable(self.data, self)
        self.setCentralWidget(self.tab)

    def resizeEvent(self, event):
        super(MainWindow, self).resizeEvent(event)
        tacmaopt.opt.Hx = self.size().width()
        tacmaopt.opt.Hy = self.size().height()

    def moveEvent(self, event):
        super(MainWindow, self).moveEvent(event)
        tacmaopt.opt.x0 = self.x()
        tacmaopt.opt.y0 = self.y()

    def _autosave(self):
        'save to opt.autosave'
        self.data.write_data()

    def _bautosave(self):
        'save to opt.backup_autosave'
        self.data.write_data(tacmaopt.opt.backup_fn)

def main():
    try:
        # config.py will be copied to actual directory
        # only during installation procedure.
        # If there is no such module -> we are in the debug session
        import config
        import os.path
        tacmaopt.ProgOptions.wdir = config.working_directory
        tacmaopt.ProgOptions.ver = config.version
        if not os.path.exists(tacmaopt.ProgOptions.wdir):
            os.makedirs(tacmaopt.ProgOptions.wdir)
    except:
        tacmaopt.ProgOptions.wdir = '.'
        tacmaopt.ProgOptions.ver = 'Debug'


    # -- read options
    tacmaopt.opt.read()

    # -- initialize qt application
    app = QtWidgets.QApplication(sys.argv)

    mw = MainWindow(tacmaopt.opt.wfile)
    mw.show()

    # start gui loop
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
