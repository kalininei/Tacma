#!/usr/bin/env python

import sys
from PyQt5 import QtWidgets, QtCore, QtGui
from mtab import MainWindowTable
import tacmaopt
from wfile import TacmaData
import bproc


class MainWindow(QtWidgets.QMainWindow):

    class DataInfoEmitter(QtCore.QObject):
        """ signal emitted when active task changes.
            int - new active task id or -1 if all stopped.
        """
        current_activity_changed = QtCore.pyqtSignal(int)

        def __init__(self):
            super(MainWindow.DataInfoEmitter, self).__init__()

    def __init__(self, fn):
        super(MainWindow, self).__init__()
        self.emitter = MainWindow.DataInfoEmitter()
        self.data = TacmaData(fn, self.emitter)
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
        exit_action.setShortcut(QtGui.QKeySequence.Close)
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

    def event(self, event):
        if event.type() == QtCore.QEvent.WindowStateChange:
            if self.isMinimized():
                self.setHidden(True)
                event.ignore()
                return True
        elif event.type() == QtCore.QEvent.Close:
            self.setHidden(True)
            event.ignore()
            return True
        return False

    def _autosave(self):
        'save to opt.autosave'
        self.data.write_data()

    def _bautosave(self):
        'save to opt.backup_autosave'
        self.data.write_data(tacmaopt.opt.backup_fn)


class TrayIcon(QtWidgets.QSystemTrayIcon):
    def __init__(self, app, mw):
        super(TrayIcon, self).__init__(bproc.get_icon('icon-stop'), app)
        self.win = mw
        self.data = mw.data
        self.win.emitter.current_activity_changed.connect(self._act_changed)
        self.setupUI()

    def setupUI(self):
        self.activated.connect(self._act_activated)
        self.menu = QtWidgets.QMenu()
        self._def_buildmenu()
        self.setContextMenu(self.menu)

    def _def_buildmenu(self):
        import functools
        self.menu.clear()

        #Stop all activities
        act = QtWidgets.QAction('Stop', self)
        act.triggered.connect(
            functools.partial(self._act_actchecked, 0, False))
        self.menu.addAction(act)
        self.menu.addSeparator()
        #Place all current activities
        for a in self.data.acts:
            if a.is_alive():
                act = QtWidgets.QAction(a.name, self)
                act.setCheckable(True)
                act.setChecked(a.is_on())
                act.toggled.connect(
                        functools.partial(self._act_actchecked, a.iden))
                self.menu.addAction(act)
        self.menu.addSeparator()
        #Exit
        act = QtWidgets.QAction('Exit', self)
        act.triggered.connect(QtWidgets.qApp.quit)
        self.menu.addAction(act)

    def _act_activated(self, reason):
        'mouse press on icon'
        if reason == self.Context:
            self._def_buildmenu()
        elif reason == self.Trigger:
            if self.win.isHidden():
                self.win.setHidden(False)
                self.win.raise_()
            else:
                self.win.setHidden(True)

    def _act_actchecked(self, iden, b):
        if b:
            self.data.turn_on(iden)
        else:
            self.data.turn_off()
        self.win.tab.model().update_column('status')

    def _act_changed(self, iden):
        if iden == -1:
            self.setIcon(bproc.get_icon('icon-stop'))
            self.setToolTip('')
        else:
            self.setIcon(bproc.get_icon('icon-run'))
            self.setToolTip('%s' % self.data._gai(iden).name)


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

    # -- tray icon
    ticon = TrayIcon(app, mw)
    ticon.show()

    # start gui loop
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
