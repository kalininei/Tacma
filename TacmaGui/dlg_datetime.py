import datetime
from PyQt5 import QtWidgets, QtCore


class DateTimeDialog(QtWidgets.QDialog):
    def __init__(self, caption=None, init_date_time=None, parent=None):
        super(DateTimeDialog, self).__init__(parent)
        if caption is None:
            caption = "Date/Time picker"
        self.setWindowTitle(caption)

        # button box
        bbox = QtWidgets.QDialogButtonBox(self)
        bbox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel |
                                QtWidgets.QDialogButtonBox.Ok)
        bbox.accepted.connect(self.accept)
        bbox.rejected.connect(self.reject)

        # calendar
        self.calendar = QtWidgets.QCalendarWidget(self)

        # time picker
        self.timeedit = QtWidgets.QTimeEdit(self)
        self.timeedit.setDisplayFormat('hh:mm:ss')

        # layout
        mainlayout = QtWidgets.QVBoxLayout()
        mainlayout.addWidget(self.calendar)
        mainlayout.addWidget(self.timeedit)
        mainlayout.addWidget(bbox)
        self.setLayout(mainlayout)

        if init_date_time is not None:
            self.set_date_time(init_date_time)

    def set_date_time(self, dt):
        time = QtCore.QTime(
            dt.hour,
            dt.minute,
            dt.second)
        date = QtCore.QDate(
            dt.year,
            dt.month,
            dt.day)
        self.timeedit.setTime(QtCore.QTime(time))
        self.calendar.setSelectedDate(date)

    def accept(self):
        self.setResult(self.Accepted)
        super(DateTimeDialog, self).accept()

    def reject(self):
        self.setResult(self.Rejected)
        super(DateTimeDialog, self).reject()

    def get_result(self):
        qdate = self.calendar.selectedDate()
        qtime = self.timeedit.time()
        ret = datetime.datetime(
            qdate.year(), qdate.month(), qdate.day(),
            qtime.hour(), qtime.minute(), qtime.second())
        return ret
