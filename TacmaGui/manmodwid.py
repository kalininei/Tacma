import functools
import copy
import bproc
from PyQt5 import QtWidgets, QtCore, QtGui
import tacmaopt
from dlg_datetime import DateTimeDialog


class ManualModifyDialog(QtWidgets.QDialog):
    def __init__(self, dt, act, parent=None):
        super(ManualModifyDialog, self).__init__(parent)
        self.act = act
        self.dt = dt
        self.setWindowTitle('Manual modify activity: %s' % act.name)
        self.resize(tacmaopt.opt.mod_window_Hx, tacmaopt.opt.mod_window_Hy)
        self.move(tacmaopt.opt.mod_window_x0, tacmaopt.opt.mod_window_y0)
        self.onofftab = OnoffTable(dt, act, self)
        self.pritab = PriTable(dt, act, self)

        # button box
        bbox = QtWidgets.QDialogButtonBox(self)
        bbox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel |
                                QtWidgets.QDialogButtonBox.Ok)
        bbox.accepted.connect(self.accept)
        bbox.rejected.connect(self.reject)

        # labels
        myfont = QtGui.QFont()
        myfont.setBold(True)
        onoff_label = QtWidgets.QLabel("Activity on/off", self)
        onoff_label.setAlignment(QtCore.Qt.AlignHCenter)
        onoff_label.setFont(myfont)
        pri_label = QtWidgets.QLabel("Priority changes", self)
        pri_label.setAlignment(QtCore.Qt.AlignHCenter)
        pri_label.setFont(myfont)

        # fill layout
        mainlayout = QtWidgets.QGridLayout(self)
        mainlayout.addWidget(onoff_label, 0, 0)
        mainlayout.addWidget(pri_label, 0, 1)
        mainlayout.addWidget(self.onofftab, 1, 0)
        mainlayout.addWidget(self.pritab, 1, 1)
        mainlayout.addWidget(bbox, 2, 0, 2, 0)
        mainlayout.setColumnStretch(0, 3)
        mainlayout.setColumnStretch(1, 2)
        self.setLayout(mainlayout)

    def resizeEvent(self, event):  # NOQA
        'write window size on options file'
        super(ManualModifyDialog, self).resizeEvent(event)
        tacmaopt.opt.mod_window_Hx = self.size().width()
        tacmaopt.opt.mod_window_Hy = self.size().height()

    def moveEvent(self, event):  # NOQA
        'write window position on options file'
        super(ManualModifyDialog, self).moveEvent(event)
        tacmaopt.opt.mod_window_x0 = self.x()
        tacmaopt.opt.mod_window_y0 = self.y()

    def _modify_onoff(self):
        newd = copy.deepcopy(self.onofftab.model().onoff)
        if len(self.act.onoff) % 2 == 1:
            newd.append(self.act.onoff[-1])
        if newd != self.act.onoff:
            self.dt.reset_action_onoff(self.act.iden, newd)

    def _modify_prior(self):
        newd = copy.deepcopy(self.pritab.model().pri)
        if newd != self.act.prior:
            self.dt.reset_action_prior(self.act.iden, newd)

    def accept(self):
        txt = "Do you really want to make manual changes to action %s?"\
            % self.act.name
        a = QtWidgets.QMessageBox.question(
            None, "Confirmation",
            txt, QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        if a == QtWidgets.QMessageBox.Yes:
            self.setResult(self.Accepted)
            self._modify_onoff()
            self._modify_prior()

            super(ManualModifyDialog, self).accept()

    def reject(self):
        self.setResult(self.Rejected)
        super(ManualModifyDialog, self).reject()


class OnoffTable(QtWidgets.QTableView):
    def __init__(self, dt, act, parent):
        super(OnoffTable, self).__init__(parent)
        # model and delegate
        self.setModel(OnoffViewModel(
            act.created, dt.curtime_to_int(), act.onoff))
        self.setItemDelegate(OnoffTableDelegate(dt))

        # stretch and scroll
        for i in range(3):
            self.horizontalHeader().setSectionResizeMode(
                i, QtWidgets.QHeaderView.Stretch)
        self.scrollToBottom()

        # context menu
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._context_menu)

    def _context_menu(self, pnt):
        index = self.indexAt(pnt)
        menu = QtWidgets.QMenu(self)
        # modify a row
        act = QtWidgets.QAction("Modify", self)
        act.setEnabled(index.isValid() and index.column() < 3)
        act.triggered.connect(functools.partial(self._mod_action, index))
        menu.addAction(act)
        # add a row
        act = QtWidgets.QAction("Add", self)
        act.setEnabled(True)
        act.triggered.connect(self._add_action)
        menu.addAction(act)
        # Remove raw
        act = QtWidgets.QAction("Remove", self)
        act.setEnabled(index.isValid())
        act.triggered.connect(functools.partial(self._rem_action, index.row()))
        menu.addAction(act)

        menu.popup(self.viewport().mapToGlobal(pnt))

    def _mod_action(self, index):
        self.edit(index)

    def _add_action(self):
        tmmax = self.model().maxtime
        tmmax = self.itemDelegate()._dt.int_to_time(tmmax)
        dlg1 = DateTimeDialog("Start date", tmmax, self)
        if not dlg1.exec_():
            return
        t1 = dlg1.get_result()
        dlg2 = DateTimeDialog("End date", tmmax, self)
        if not dlg2.exec_():
            return
        t2 = dlg2.get_result()
        t1 = self.itemDelegate()._dt.time_to_int(t1)
        t2 = self.itemDelegate()._dt.time_to_int(t2)
        if self.model()._check_interval([t1, t2]):
            self.model()._append_interval([t1, t2])

    def _rem_action(self, irow):
        self.model()._remove_row(irow)


class OnoffTableDelegate(QtWidgets.QItemDelegate):
    def __init__(self, dt, parent=None):
        super(OnoffTableDelegate, self).__init__(parent)
        self._dt = dt

    def _time_to_string(self, inttime):
        time = self._dt.int_to_time(inttime)
        return time.strftime("%Y/%m/%d,  %H:%M:%S")

    def _parse_interval(self, sint):
        try:
            a = sint.split(':')
            if len(a) != 3:
                raise
            h = int(a[0])
            m = int(a[1])
            s = int(a[2])
            if h < 0 or m < 0 or s < 0:
                raise
            if m >= 60 or s >= 60:
                raise
            return s + 60 * m + 3600 * h
        except:
            QtWidgets.QMessageBox.warning(
                None, "Warning", "Error parsing time interval string")
            raise ValueError

    def paint(self, painter, option, index):
        rect = QtCore.QRect(option.rect)
        inttime = index.data()
        if index.column() < 2:
            txt = self._time_to_string(inttime)
        else:
            txt = bproc.sec_to_strtime_interval(inttime, False)
        self.drawDisplay(painter, option, rect, txt)

    def createEditor(self, parent, option, index):  # NOQA
        "overriden"
        if index.column() in [0, 1]:
            w = DateTimeDialog(None, None, self.parent())
            w.setModal(True)
            return w
        return super(OnoffTableDelegate, self).createEditor(
            parent, option, index)

    def setEditorData(self, editor, index):  # NOQA
        if index.column() in [0, 1]:
            editor.set_date_time(
                self._dt.int_to_time(index.data()))
        else:
            editor.setText(bproc.sec_to_strtime_interval(index.data(), False))

    def setModelData(self, editor, model, index):  # NOQA
        if index.column() in [0, 1]:
            if editor.result() == QtWidgets.QDialog.Accepted:
                v = editor.get_result()
                model.setData(
                    index, self._dt.time_to_int(v), QtCore.Qt.EditRole)
        else:
            tm1 = model.data(
                model.index(index.row(), 0), QtCore.Qt.DisplayRole)
            tm = self._parse_interval(str(editor.text()))
            model.setData(
                model.index(index.row(), 1), tm + tm1, QtCore.Qt.EditRole)


class OnoffViewModel(QtCore.QAbstractTableModel):
    def __init__(self, mintime, maxtime, onoff):
        super(OnoffViewModel, self).__init__()
        self.onoff = copy.deepcopy(onoff)
        if len(self.onoff) % 2 == 1:
            self.onoff.pop()
        self.mintime = mintime
        self.maxtime = maxtime

    def _remove_row(self, irow):
        self.beginRemoveRows(QtCore.QModelIndex(), irow, irow)
        del self.onoff[2 * irow]
        del self.onoff[2 * irow]
        self.removeRow(irow)
        self.endRemoveRows()

    def _check_interval(self, interval):
        def invalid():
            QtWidgets.QMessageBox.warning(
                None, "Warning", "Input interval is not valid")
            return False

        if interval[1] <= interval[0]:
            return invalid()
        if interval[0] < self.mintime:
            return invalid()
        if interval[1] > self.maxtime:
            return invalid()
        return True

    def _append_interval(self, interval):
        self.beginResetModel()
        it = iter(self.onoff)
        ab = [(a, b, 1) for a, b in zip(it, it)]
        pw = bproc.PieceWiseFun.raw_create(ab)
        pw.add_section(interval[0], interval[1], 1)
        del self.onoff[:]
        for it in pw._dt:
            self.onoff.append(int(it[0]))
            self.onoff.append(int(it[1]))
        self.endResetModel()

    def rowCount(self, parent=None):  # NOQA
        "overriden"
        return len(self.onoff) / 2

    def columnCount(self, parent=None):  # NOQA
        "overriden"
        return 3

    def headerData(self, section, orientation, role):  # NOQA
        "overriden"
        if role == QtCore.Qt.DisplayRole:
            s = None
            if orientation == QtCore.Qt.Horizontal:
                if section == 0:
                    s = "started"
                elif section == 1:
                    s = "finished"
                else:
                    s = "duration"
            return QtCore.QVariant(s)

    def data(self, index, role):
        "overriden"
        if not index.isValid():
            return None
        if role == QtCore.Qt.DisplayRole:
            ir = 2 * index.row()
            if index.column() == 0:
                return self.onoff[ir]
            elif index.column() == 1:
                return self.onoff[ir + 1]
            else:
                return self.onoff[ir + 1] - self.onoff[ir]
        return None

    def flags(self, index):
        return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable |\
            QtCore.Qt.ItemIsSelectable

    def setData(self, index, value, role):  # NOQA
        if role == QtCore.Qt.EditRole:
            ir = index.row()
            # ignore if value was not changed
            if value == self.data(index, QtCore.Qt.DisplayRole):
                return False

            # check if value is valid
            newinterval = self.onoff[2 * ir:2 * ir + 2]

            if not self._check_interval(newinterval):
                return False

            # set value
            if index.column() == 0:
                newinterval[0] = value
            elif index.column() == 1:
                newinterval[1] = value
            self._remove_row(ir)
            self._append_interval(newinterval)
            return True

        return True


class PriTable(QtWidgets.QTableView):
    def __init__(self, dt, act, parent):
        super(PriTable, self).__init__(parent)
        # model and delegate
        self.setModel(PriViewModel(
            act.created, dt.curtime_to_int(), act.prior))
        self.setItemDelegate(PriTableDelegate(dt))
        # stretch and scroll
        for i in range(2):
            self.horizontalHeader().setSectionResizeMode(
                i, QtWidgets.QHeaderView.Stretch)
        self.scrollToBottom()

        # context menu
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._context_menu)

    def _context_menu(self, pnt):
        index = self.indexAt(pnt)
        menu = QtWidgets.QMenu(self)
        # modify a row
        act = QtWidgets.QAction("Modify", self)
        act.setEnabled(index.isValid())
        act.triggered.connect(functools.partial(self._mod_action, index))
        menu.addAction(act)
        # add a row
        act = QtWidgets.QAction("Add", self)
        act.setEnabled(True)
        act.triggered.connect(self._add_action)
        menu.addAction(act)
        # Remove raw
        act = QtWidgets.QAction("Remove", self)
        act.setEnabled(index.isValid())
        act.triggered.connect(functools.partial(self._rem_action, index.row()))
        menu.addAction(act)

        menu.popup(self.viewport().mapToGlobal(pnt))

    def _mod_action(self, index):
        self.edit(index)

    def _add_action(self):
        tmmax = self.model().maxtime
        tmmax = self.itemDelegate()._dt.int_to_time(tmmax)
        dlg1 = DateTimeDialog("Start date", tmmax, self)
        if not dlg1.exec_():
            return
        t1 = dlg1.get_result()
        t1 = self.itemDelegate()._dt.time_to_int(t1)
        if self.model()._check_starttime(t1):
            self.model()._append_value(t1, 1.0)

    def _rem_action(self, irow):
        self.model()._remove_row(irow)


class PriTableDelegate(QtWidgets.QItemDelegate):
    def __init__(self, dt, parent=None):
        super(PriTableDelegate, self).__init__(parent)
        self._dt = dt

    def paint(self, painter, option, index):
        rect = QtCore.QRect(option.rect)
        d = index.data()
        if index.column() == 0:
            time = self._dt.int_to_time(d)
            txt = time.strftime("%Y/%m/%d,  %H:%M:%S")
        else:
            txt = str(d)
        self.drawDisplay(painter, option, rect, txt)

    def createEditor(self, parent, option, index):  # NOQA
        "overriden"
        if index.column() == 0:
            w = DateTimeDialog(None, None, self.parent())
            w.setModal(True)
            return w
        return super(PriTableDelegate, self).createEditor(
            parent, option, index)

    def setModelData(self, editor, model, index):  # NOQA
        if index.column() == 1:
            model.setData(
                index, float(editor.text()), QtCore.Qt.EditRole)
        elif index.column() == 0:
            v = editor.get_result()
            model.setData(
                index, self._dt.time_to_int(v), QtCore.Qt.EditRole)

    def setEditorData(self, editor, index):  # NOQA
        if index.column() == 0:
            editor.set_date_time(
                self._dt.int_to_time(index.data()))
        else:
            editor.setText(str(index.data()))


class PriViewModel(QtCore.QAbstractTableModel):
    def __init__(self, mintime, maxtime, pri):
        super(PriViewModel, self).__init__()
        self.pri = copy.deepcopy(pri)
        self.mintime = mintime
        self.maxtime = maxtime

    def _remove_row(self, irow):
        self.beginRemoveRows(QtCore.QModelIndex(), irow, irow)
        del self.pri[irow]
        self.removeRow(irow)
        self.endRemoveRows()

    def _check_starttime(self, tm):
        def invalid():
            QtWidgets.QMessageBox.warning(
                None, "Warning", "Input time is not valid")
            return False

        if tm < self.mintime:
            return invalid()
        if tm > self.maxtime:
            return invalid()
        return True

    def _append_value(self, tm, val):
        insert_at = 0
        while insert_at < len(self.pri) and self.pri[insert_at][0] < tm:
            insert_at += 1
        if insert_at < len(self.pri) and self.pri[insert_at] == tm:
            self.setData(self.index(insert_at, 1), val)
            return
        self.beginInsertRows(QtCore.QModelIndex(), insert_at, insert_at)
        self.insertRow(insert_at)
        self.pri.insert(insert_at, (tm, val))
        self.endInsertRows()
        self.setData(self.index(insert_at, 0), tm, QtCore.Qt.EditRole)
        self.setData(self.index(insert_at, 1), val, QtCore.Qt.EditRole)

    def rowCount(self, parent=None):  # NOQA
        "overriden"
        return len(self.pri)

    def columnCount(self, parent=None):  # NOQA
        "overriden"
        return 2

    def headerData(self, section, orientation, role):  # NOQA
        "overriden"
        if role == QtCore.Qt.DisplayRole:
            s = None
            if orientation == QtCore.Qt.Horizontal:
                if section == 0:
                    s = "started"
                elif section == 1:
                    s = "priority"
            return QtCore.QVariant(s)

    def data(self, index, role):
        "overriden"
        if not index.isValid():
            return None
        if role == QtCore.Qt.DisplayRole:
            ir = index.row()
            if index.column() == 0:
                return self.pri[ir][0]
            elif index.column() == 1:
                return self.pri[ir][1]
        return None

    def flags(self, index):
        return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable |\
            QtCore.Qt.ItemIsSelectable

    def setData(self, index, value, role):  # NOQA
        if role == QtCore.Qt.EditRole:
            # ignore if value was not changed
            if value == self.data(index, QtCore.Qt.DisplayRole):
                return False

            # check if value is valid
            if index.column() == 0:
                if not self._check_starttime(value):
                    return False
            if index.column() == 1:
                if value < 0:
                    QtWidgets.QMessageBox.warning(
                        None, "Warning", "Input priority is not valid")
                    return False

            # set value
            if index.column() == 0:
                self.pri[index.row()] = (value, self.pri[index.row()][1])
            if index.column() == 1:
                self.pri[index.row()] = (self.pri[index.row()][0], value)
            return True

        return True
