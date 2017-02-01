from PyQt5 import QtWidgets, QtCore
import tacmaopt
from addeditwid import AddEditDialog
from manmodwid import ManualModifyDialog
import bproc
import functools


class ViewModel(QtCore.QAbstractTableModel):
    def __init__(self, dt):
        super(ViewModel, self).__init__()
        self.dt = dt
        dt.emitter.subscribe(self, self._tacma_data_changed)

    #table columns names and order
    cnames = {'status': (0, ''),
              'title': (1, 'Title'),
              'id': (2, 'id'),
              'prior': (3, 'Priority'),
              'weight': (4, 'Weight'),
              'created': (5, 'Created'),
              'finished': (6, 'Finished'),
              'l24h': (7, 'Last 24h'),
              'l1w': (8, 'Last week'),
              'l4w': (9, 'Last 4 weeks'),
              'lses': (10, 'Last session'),
              'idle': (11, 'Idle'),
              }

    def rowCount(self, parent=None):  # NOQA
        "overriden"
        return self.dt.act_count()

    def columnCount(self, parent=None):  # NOQA
        "overriden"
        return len(self.cnames)

    def headerData(self, section, orientation, role):  # NOQA
        "overriden"
        if role == QtCore.Qt.DisplayRole:
            s = None
            if orientation == QtCore.Qt.Horizontal:
                for k in self.cnames.keys():
                    if section == self.cnames[k][0]:
                        s = self.cnames[k][1]
            return QtCore.QVariant(s)

    def data(self, index, role):
        "overriden"
        if not index.isValid():
            return None
        if role == QtCore.Qt.DisplayRole:
            iden = self.get_iden(index)
            if index.column() == self.cnames['id'][0]:
                return iden
            elif index.column() == self.cnames['title'][0]:
                return self.dt.name(iden)
            elif index.column() == self.cnames['prior'][0]:
                return self.dt.priority(iden)
            elif index.column() == self.cnames['weight'][0]:
                return str(round(self.dt.weight(iden) * 100)) + ' %'
            elif index.column() == self.cnames['created'][0]:
                return self.dt.created_time(iden)
            elif index.column() == self.cnames['finished'][0]:
                return self.dt.finished_time(iden)
            elif index.column() == self.cnames['l24h'][0]:
                return (self.dt.stat.must_time(iden, 86400),
                        self.dt.stat.real_time(iden, 86400))
            elif index.column() == self.cnames['l1w'][0]:
                return (self.dt.stat.must_time(iden, 604800),
                        self.dt.stat.real_time(iden, 604800))
            elif index.column() == self.cnames['l4w'][0]:
                return (self.dt.stat.must_time(iden, 2419200),
                        self.dt.stat.real_time(iden, 2419200))
            elif index.column() == self.cnames['lses'][0]:
                return self.dt.stat.last_session(iden)
            elif index.column() == self.cnames['idle'][0]:
                return self.dt.stat.idle_since(iden)
        elif role == QtCore.Qt.CheckStateRole:
            iden = self.get_iden(index)
            if index.column() == self.cnames['status'][0]:
                return QtCore.Qt.Checked if self.dt.is_on(iden) \
                    else QtCore.Qt.Unchecked
        return None

    def setData(self, index, value, role):  # NOQA
        if not index.isValid():
            return None
        if index.column() == 0:
            if role == QtCore.Qt.CheckStateRole:
                if value == QtCore.Qt.Checked:
                    self.dt.turn_on(self.get_iden(index))
                else:
                    self.dt.turn_off()
            return True
        return False

    def flags(self, index):
        "overriden"
        ret = QtCore.Qt.NoItemFlags | QtCore.Qt.ItemIsEnabled
        if (index.column() == 0):
            ret |= QtCore.Qt.ItemIsUserCheckable
        return ret

    def add_action(self, name, priority, comment):
        'adds a new action. Returns its iden'
        ret = self.dt.add_action(name, priority, comment)
        self.layoutChanged.emit()
        return ret

    def edit_act(self, index, newval):
        ' (table index, (name, priority, comment)). Set new data to action'
        i = self.get_iden(index)
        self.dt.change_action_name(i, newval[0])
        self.dt.change_action_prior(i, newval[1])
        self.dt.set_comment(i, newval[2])

    def edit_act_by_iden(self, iden, newval):
        ' (task identifier, (name, priority, comment)). Set new data to action'
        self.dt.change_action_name(iden, newval[0])
        self.dt.change_action_prior(iden, newval[1])
        self.dt.set_comment(iden, newval[2])

    def finish(self, index):
        self.dt.finish(self.get_iden(index))
        self.layoutChanged.emit()

    def remove(self, index):
        txt = 'Are you sure you want to completely remove '
        txt += 'action %s from all statistics?' % self.get_act(index).name
        a = QtWidgets.QMessageBox.question(
            None, "Tacma Confirmation",
            txt, QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        if a == QtWidgets.QMessageBox.Yes:
            self.dt.remove(self.get_iden(index))
            self.layoutChanged.emit()

    def get_act(self, index):
        '->Act. Get action by table index'
        return self.dt.acts[index.row()]

    def get_iden(self, index):
        '->int. Get id by table index'
        return self.get_act(index).iden

    def timer_view_update(self):
        'update columns which change through time'
        self.update_column('l24h')
        self.update_column('l1w')
        self.update_column('l4w')
        self.update_column('lses')

    def update_column(self, ccode):
        'update column by its ccname'
        col = self.cnames[ccode][0]
        i0 = self.createIndex(0, col)
        i1 = self.createIndex(self.rowCount() - 1, col)
        self.dataChanged.emit(i0, i1)

    def update_row(self, iden):
        'update row by task identifier'
        iup = -1
        for i, a in enumerate(self.dt.acts):
            if a.iden == iden:
                iup = i
                break
        if iup == -1:
            return
        i0 = self.createIndex(iup, 0)
        i1 = self.createIndex(iup, self.columnCount() - 1)
        self.dataChanged.emit(i0, i1)

    def _tacma_data_changed(self, event, iden):
        if event == 'ActiveTaskChanged':
            self.update_column('status')
        elif event == 'PriorityChanged':
            self.update_column('prior')
        elif event == 'NameChanged':
            self.update_column('title')
        elif event == 'ManualDataChanged':
            self.update_row(iden)


class TableDelegate(QtWidgets.QItemDelegate):
    """ delegate for table:
    """
    def __init__(self, dt, parent=None):
        self.dt = dt
        super(TableDelegate, self).__init__(parent)

    def paint(self, painter, option, index):
        if not index.isValid():
            return
        if (index.column() in [ViewModel.cnames[i][0]
                               for i in ['created', 'finished']]):
            d = index.data()
            #write date
            rect = QtCore.QRect(option.rect)
            self.drawDisplay(painter, option, rect, d.strftime('%Y-%m-%d'))
        elif (index.column() in [ViewModel.cnames[i][0]
                                 for i in ['l24h', 'l1w', 'l4w']]):
            d = index.data()
            #write statistics
            rect = QtCore.QRect(option.rect)
            h = int(d[1] / 3600)
            m = int((d[1] - h * 3600) / 60)
            s = int(d[1] - h * 3600 - 60 * m)
            p = int(d[1] / d[0] * 100) if d[0] != 0 else 0
            txt = '%i:%02i:%02i / %i %%' % (h, m, s, p)
            self.drawDisplay(painter, option, rect, txt)
        elif index.column() in [ViewModel.cnames[i][0]
                                for i in ['lses', 'idle']]:
            d = index.data()
            if d is not None:
                if d < 0:
                    txt = ">%i weeks" % tacmaopt.opt.minactual
                else:
                    txt = bproc.sec_to_strtime_interval(d, True)
                rect = QtCore.QRect(option.rect)
                self.drawDisplay(painter, option, rect, txt)
        else:
            super(TableDelegate, self).paint(painter, option, index)


class MainWindowTable(QtWidgets.QTableView):
    def __init__(self, dt, parent):
        super(MainWindowTable, self).__init__(parent)

        # model and delegate
        self.setModel(ViewModel(dt))
        delegate = TableDelegate(dt, self)
        self.setItemDelegate(delegate)

        # contex menu
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._context_menu)

        #autoupdate table
        self.view_update = QtCore.QTimer(self)
        self.view_update.timeout.connect(self.model().timer_view_update)
        self.view_update.start(tacmaopt.opt.update_interval * 1000)

        #column widths
        for k, v in tacmaopt.opt.colwidths.iteritems():
            info = ViewModel.cnames[k]
            self.setColumnWidth(info[0], v)

        #column visible
        for k, v in tacmaopt.opt.colvisible.iteritems():
            info = ViewModel.cnames[k]
            self.setColumnHidden(info[0], not v)

        # header after setting widths
        self.horizontalHeader().sectionResized.connect(self._secresized)

    def _secresized(self, index, oldval, newval):
        if newval < 10:
            return
        for k, v in ViewModel.cnames.iteritems():
            if v[0] == index:
                tacmaopt.opt.colwidths[k] = newval
                return

    def _context_menu(self, pnt):
        index = self.indexAt(pnt)

        menu = QtWidgets.QMenu(self)
        #Edit
        act = QtWidgets.QAction("Edit", self)
        act.setEnabled(index.isValid())
        act.triggered.connect(functools.partial(self._edit_action, index))
        menu.addAction(act)
        #Add
        act = QtWidgets.QAction("Add", self)
        act.triggered.connect(self._add_action)
        menu.addAction(act)
        #Finish
        act = QtWidgets.QAction("Finish", self)
        act.setEnabled(index.isValid() and
                       self.model().get_act(index).is_alive())
        act.triggered.connect(
            functools.partial(self._fin_action, index))
        menu.addAction(act)
        #Remove
        act = QtWidgets.QAction("Remove", self)
        act.setEnabled(index.isValid())
        act.triggered.connect(functools.partial(self._rem_action, index))
        menu.addAction(act)
        #Manual modify
        act = QtWidgets.QAction("Manual modify", self)
        act.setEnabled(index.isValid())
        act.triggered.connect(
            functools.partial(self._mod_action, index))
        menu.addAction(act)

        menu.popup(self.viewport().mapToGlobal(pnt))

    def _add_action(self):
        def applyfunc(name, prior, comm):
            if self.__tmp is None:
                self.__tmp = self.model().add_action(name, prior, comm)
            else:
                self.model().edit_act_by_iden(
                    self.__tmp, (name, prior, comm))

        self.__tmp = None
        AddEditDialog(applyfunc, None, self).exec_()

    def _edit_action(self, index):
        def applyfunc(name, prior, comm):
            self.model().edit_act(index, (name, prior, comm))

        a = self.model().get_act(index)
        AddEditDialog(applyfunc, a, self).exec_()

    def _mod_action(self, index):
        a = self.model().get_act(index)
        ManualModifyDialog(self.model().dt, a, self).exec_()

    def _fin_action(self, index):
        self.model().finish(index)

    def _rem_action(self, index):
        self.model().remove(index)
