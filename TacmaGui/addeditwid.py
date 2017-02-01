from PyQt5 import QtWidgets, QtGui
import tacmaopt


class AddEditDialog(QtWidgets.QDialog):
    def __init__(self, apply_func, act=None, parent=None):
        super(AddEditDialog, self).__init__(parent)
        self.apply_func = apply_func
        self.setWindowTitle('Add/Edit Activity')
        # self.resize(600, self.height())
        self.resize(tacmaopt.opt.edit_window_Hx, tacmaopt.opt.edit_window_Hy)
        self.move(tacmaopt.opt.edit_window_x0, tacmaopt.opt.edit_window_y0)
        layout = QtWidgets.QGridLayout()
        labtit = QtWidgets.QLabel('Action title', self)
        labpr = QtWidgets.QLabel('Priority', self)
        labcom = QtWidgets.QLabel('Comments', self)
        t = act.name if act else 'Action'
        self.edtit = QtWidgets.QLineEdit(t, self)
        t = act.current_priority() if act else '1.0'
        self.edpr = QtWidgets.QLineEdit(str(t), self)
        t = act.comment if act else ''
        self.edcom = QtWidgets.QTextEdit(self)
        self.edcom.setPlainText(t)
        self.edcom.setFont(QtGui.QFont('Courier', 10))
        bbox = QtWidgets.QDialogButtonBox(self)
        bbox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel |
                                QtWidgets.QDialogButtonBox.Ok |
                                QtWidgets.QDialogButtonBox.Apply)
        bbox.accepted.connect(self.accept)
        bbox.rejected.connect(self.reject)
        ab = bbox.button(QtWidgets.QDialogButtonBox.Apply)
        ab.clicked.connect(self.applied)

        layout.addWidget(labtit, 0, 0)
        layout.addWidget(labpr, 1, 0)
        layout.addWidget(labcom, 2, 0)
        layout.addWidget(self.edtit, 0, 1)
        layout.addWidget(self.edpr, 1, 1)
        layout.addWidget(self.edcom, 2, 1)
        layout.addWidget(bbox, 3, 0, 1, 2)

        self.setLayout(layout)

    def applied(self):
        try:
            self.apply_func(*self.ret_value())
        except Exception as e:
            import traceback
            traceback.print_exc()
            QtWidgets.QMessageBox.warning(self, "Warning",
                                          "Invalid Input: %s" % str(e))
            return False
        return True

    def accept(self):
        if self.applied():
            super(AddEditDialog, self).accept()

    def ret_value(self):
        '-> (str name, float priority, str comments)'
        pr = float(self.edpr.text())
        if pr < 0 or pr > 10:
            raise Exception("Priority is a float number within [0, 10.0]")
        nm = self.edtit.text()
        if len(nm) < 3:
            raise Exception("Title should contain at least 3 characters")
        return (nm, pr, self.edcom.toPlainText())

    def resizeEvent(self, event):  # NOQA
        'write window size on options file'
        super(AddEditDialog, self).resizeEvent(event)
        tacmaopt.opt.edit_window_Hx = self.size().width()
        tacmaopt.opt.edit_window_Hy = self.size().height()

    def moveEvent(self, event):  # NOQA
        'write window position on options file'
        super(AddEditDialog, self).moveEvent(event)
        tacmaopt.opt.edit_window_x0 = self.x()
        tacmaopt.opt.edit_window_y0 = self.y()
