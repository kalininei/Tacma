"Tray icon widget"
import functools
import bproc
from PyQt5 import QtWidgets


class TrayMenu(QtWidgets.QMenu):
    'Menu which is not closed after CheckBox click'
    def __init__(self, data, parent=None):
        'data - TacmaData object, parent - None'
        super(TrayMenu, self).__init__(parent)
        self.data = data
        #Otherwise first appearence of menu goes under screen on X11
        self.rebuild()

    def mouseReleaseEvent(self, e):
        'overriden to not close menu after trigger'
        action = self.activeAction()
        if action is not None and action.isEnabled():
            action.setEnabled(False)
            super(TrayMenu, self).mouseReleaseEvent(e)
            action.setEnabled(True)
            action.trigger()
        else:
            super(TrayMenu, self).mouseReleaseEvent(e)

    def _add_task_action(self, task):
        """ adds task action to menu list
            returns an action
        """
        if not task.is_alive():
            return

    def _act_task_checked(self, iden, b):
        """ called when tack line is triggered
            iden - identifier of task
            b - new flag value
        """
        if b:
            self.data.turn_on(iden)
        else:
            self.data.turn_off()

    def rebuild(self):
        'rebuilds menu. Writes all task activities to self._tact'
        self.clear()
        self._tact = {}
        stop_act = QtWidgets.QAction('Stop', self)
        stop_act.triggered.connect(
            functools.partial(self._act_task_checked, 0, False))
        self.addAction(stop_act)
        self.addSeparator()
        for task in self.data.acts:
            if task.is_alive:
                act = QtWidgets.QAction(task.name, self)
                act.toggled.connect(
                        functools.partial(self._act_task_checked, task.iden))
                act.setCheckable(True)
                self.addAction(act)
                self._tact[task] = act
        self.refresh_checkboxes()
        self.addSeparator()
        exit_act = QtWidgets.QAction('Exit', self)
        exit_act.triggered.connect(QtWidgets.qApp.quit)
        self.addAction(exit_act)

    def refresh_checkboxes(self):
        'refreshed checkboxes if menu is activated'
        if self.isActiveWindow():
            for k, v in self._tact.items():
                v.toggled.disconnect()
                v.setChecked(k.is_on())
                v.toggled.connect(
                        functools.partial(self._act_task_checked, k.iden))


class TrayIcon(QtWidgets.QSystemTrayIcon):
    'Tray icon for application'
    def __init__(self, mw):
        'mw - MainWindow'
        super(TrayIcon, self).__init__(bproc.get_icon('icon-stop'),
                QtWidgets.qApp)
        self.win = mw
        self.data = mw.data
        self.win.emitter.current_activity_changed.connect(self._act_changed)
        self.setupUI()

    def setupUI(self):
        self.activated.connect(self._act_activated)
        self.menu = TrayMenu(self.data)
        self.setContextMenu(self.menu)

    def _act_activated(self, reason):
        'mouse press on icon'
        if reason == self.Context:
            self.menu.rebuild()
        elif reason == self.Trigger:
            if self.win.isHidden():
                self.win.setHidden(False)
                self.win.raise_()
            else:
                self.win.setHidden(True)

    def _act_changed(self, iden):
        if iden == -1:
            self.setIcon(bproc.get_icon('icon-stop'))
            self.setToolTip('')
        else:
            self.setIcon(bproc.get_icon('icon-run'))
            self.setToolTip('%s' % self.data._gai(iden).name)
        self.menu.refresh_checkboxes()
