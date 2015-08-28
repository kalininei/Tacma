from PyQt5 import QtWidgets, QtCore, QtGui
from mtab import MainWindowTable
import tacmaopt
from wfile import TacmaData
import bproc
from traywid import TrayIcon


class MainWindow(QtWidgets.QMainWindow):
    "application main window"
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
        # -- tray icon
        self.ticon = TrayIcon(self)
        self.ticon.show()

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
