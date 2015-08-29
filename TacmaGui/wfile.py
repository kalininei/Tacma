import os.path
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
import tacmaopt
import bproc


class Act(object):
    def __init__(self, iden, name, prior, dt):
        self.dt = dt
        self.name = name
        self.iden = iden
        self.comment = ''
        self.created = dt.curtime_to_int()
        self.finished = None
        self.prior = [(self.created, prior)]
        self.onoff = []

    def is_on(self):
        return len(self.onoff) % 2 == 1

    def is_alive(self):
        return self.finished is None

    def current_priority(self):
        return self.prior[-1][1]

    def dur_within(self, t0, t1):
        """->int. Returns actual duration in seconds
        of action at [t0, t1] time interval"""
        ret = 0
        for i, t in enumerate(self.onoff[::2]):
            tst = t
            inx = 2 * i + 1
            ten = self.onoff[inx] if inx < len(self.onoff) \
                else max(tst, t1) + 1
            ret += max(0, min(t1, ten) - max(t0, tst))
        return ret

    def _pwintervals(self, t0, t1):
        'aux function for prior_pw, work_pw'
        if t0 is None:
            t0 = self.prior[0][0]
        if t1 is None:
            t1 = self.dt.curtime_to_int()
        return (t0, t1)

    def prior_pw(self, t0=None, t1=None):
        """->PieceWiseFun.
            Returns priority as piecewise function at give interval'
        """
        ret = bproc.PieceWiseFun()
        t0, t1 = self._pwintervals(t0, t1)
        if len(self.prior) == 0:
            return ret
        for i, d in enumerate(self.prior[:-1]):
            dnext = self.prior[i + 1]
            ret.add_section(d[0], dnext[0], d[1], [t0, t1])
        ret.add_section(self.prior[-1][0], t1, self.prior[-1][1], [t0, t1])
        return ret

    def work_pw(self, t0=None, t1=None):
        """->PieceWiseFun.
            Returns activity as piecewise function at given interval'
        """
        ret = bproc.PieceWiseFun()
        if len(self.prior) == 0:
            return ret
        t0, t1 = self._pwintervals(t0, t1)
        it = iter(self.onoff)
        for st, en in zip(it, it):
            ret.add_section(st, en, 1, [t0, t1])
        if self.is_on():
            ret.add_section(self.onoff[-1], t1, 1, [t0, t1])
        return ret

    def switch(self):
        'swithes on/off status'
        self.onoff.append(self.dt.curtime_to_int())

    def set_priority(self, p):
        'sets new priority'
        if self.is_alive():
            self.prior.append((self.dt.curtime_to_int(), p))

    def save_to_xml(self, nd):
        d = ET.SubElement(nd, 'ACTION')
        d.attrib['name'] = self.name
        d.attrib['id'] = str(self.iden)
        #ON/OFF
        ET.SubElement(d, 'ONOFF').text = ' '.join(map(str, self.onoff))
        #PRIORITY
        a = []
        for i in self.prior:
            a.extend(i)
        ET.SubElement(d, 'PRIORITY').text = ' '.join(map(str, a))

        #CREATED/FINISHED
        ET.SubElement(d, 'CREATED').text = str(self.created)
        if self.finished:
            ET.SubElement(d, 'FINISHED').text = str(self.finished)

        #COMMENT
        ET.SubElement(d, 'COMMENT').text = self.comment

    @classmethod
    def read_from_xml(cls, nd, dt):
        """-> Act.
        read data from xml node tagged 'ACTION'
        """
        try:
            if nd.tag != 'ACTION':
                raise Exception('Invalid action node')
            #iden, name
            iden = int(nd.attrib['id'])
            nm = nd.attrib['name']
            ret = cls(iden, nm, 0, dt)
            #created/finished
            ret.created = int(nd.find('CREATED').text)
            fnd = nd.find('FINISHED')
            if fnd is not None:
                ret.finished = int(fnd.text)
            #onoff
            fnd = nd.find('ONOFF').text
            if fnd:
                ret.onoff = map(int, fnd.split())
            else:
                ret.onoff = []
            #priority
            a = nd.find('PRIORITY').text.split()
            ret.prior = []
            for i in range(len(a) / 2):
                ret.prior.append((int(a[2 * i]), float(a[2 * i + 1])))
            #comment
            fnd = nd.find('COMMENT')
            if fnd is not None and fnd.text:
                ret.comment = fnd.text
        except Exception as e:
            raise Exception('Invalid action xml node: %s' % str(e))

        return ret


class DataChangedEmitter(object):
    """ Events list:
        'ActiveTaskChanged' - iden = new active task or None
    """

    def __init__(self):
        # object -> function
        self.receivers = {}

    def subscribe(self, obj, func):
        self.receivers[obj] = func

    def unsubscribe(self, obj):
        self.receivers.pop(obj)

    def emit(self, event, iden=None):
        for f in self.receivers.values():
            f(event, iden)


class TacmaData(object):

    def __init__(self, fname):
        """ fname - data location
        """
        print 'Reading data from %s' % os.path.abspath(fname)
        self.fname = fname
        self.emitter = DataChangedEmitter()
        self.acts = []
        self.start_date = None
        try:
            self._read_data(self.fname)
        except:
            #if failed to read corrupted file
            from PyQt5 import QtWidgets
            if os.path.isfile(tacmaopt.opt.backup_fn):
                try:
                    self._read_data(tacmaopt.opt.backup_fn)
                    txt = "Unable to read original data."
                    txt += " Backup file was loaded"
                    QtWidgets.QMessageBox.warning(None, "Tacma Warning", txt)
                    return
                except:
                    pass
            txt = "Data is corrupted and no backup was found."
            txt += "\nStart blank session?"
            a = QtWidgets.QMessageBox.question(None, "Tacma Error",
                    txt, QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
            if a == QtWidgets.QMessageBox.No:
                quit()
            else:
                self._read_data(None)

    def _read_data(self, fn):
        'reads data from fn if it exists or creates default data list'
        if fn is None or not os.path.isfile(fn):
            self.start_date = datetime.utcnow()
        else:
            root = ET.parse(fn).getroot()
            # read start date
            a = ['YEAR', 'MONTH', 'DAY', 'HOUR', 'MIN', 'SEC']
            a = map(lambda x: int(root.find('START_DATE/%s' % x).text), a)
            self.start_date = datetime(*a)
            # read actions
            self.acts = map(lambda x: Act.read_from_xml(x, self),
                    root.findall('ACTIONS/ACTION'))
            # turn off active action
            sd = int(root.find('SAVE_TIME').text)
            aa = self._gaa()
            if aa:
                aa.onoff.append(sd)

    def write_data(self, fn=None):
        'saves current state to self.fname'
        root = ET.Element('TacmaData')
        root.attrib['version'] = tacmaopt.opt.ver
        #start date
        d = ET.SubElement(root, 'START_DATE')
        ET.SubElement(d, 'YEAR').text = str(self.start_date.year)
        ET.SubElement(d, 'MONTH').text = str(self.start_date.month)
        ET.SubElement(d, 'DAY').text = str(self.start_date.day)
        ET.SubElement(d, 'HOUR').text = str(self.start_date.hour)
        ET.SubElement(d, 'MIN').text = str(self.start_date.minute)
        ET.SubElement(d, 'SEC').text = str(self.start_date.second)
        #save date
        ET.SubElement(root, 'SAVE_TIME').text = \
                str(self.time_to_int(datetime.utcnow()))

        #actions
        d = ET.SubElement(root, 'ACTIONS')
        for a in self.acts:
            a.save_to_xml(d)

        #write to file
        bproc.xmlindent(root)
        tree = ET.ElementTree(root)
        if fn is None:
            fn = self.fname
        tree.write(fn, xml_declaration=True, encoding='utf-8')

    def time_to_int(self, tm):
        delta = tm - self.start_date
        return delta.days * 86400 + delta.seconds

    def curtime_to_int(self):
        return self.time_to_int(datetime.utcnow())

    def int_to_time(self, s):
        d = timedelta(seconds=s)
        return self.start_date + d

    def _next_iden(self):
        '->int. get not used identifier'
        if len(self.acts) == 0:
            return 0
        else:
            return max(self.acts, key=lambda x: x.iden).iden + 1

    def save_copy(self, fname):
        'save a backup copy of self.fname'
        pass

    def add_action(self, name, prior, comment=''):
        iden = self._next_iden()
        self.acts.append(Act(iden, name, prior, self))
        if comment != '':
            self.set_comment(iden, comment)

        self.write_data()

    def act_count(self):
        'number of actions'
        return len(self.acts)

    def change_action_name(self, iden, newname):
        a = self._gai(iden)
        if a.name != newname:
            a.name = newname
            self.write_data()

    def change_action_prior(self, iden, newprior):
        a = self._gai(iden)
        if a.current_priority() != newprior:
            a.set_priority(newprior)
            self.write_data()

    def set_comment(self, iden, txt):
        if self._gai(iden).comment != txt:
            self._gai(iden).comment = txt
            self.write_data()

    def get_comment(self, iden):
        return self._gai(iden).comment

    def _gai(self, iden):
        '->Act. Get action by id'
        for a in self.acts:
            if a.iden == iden:
                return a
        else:
            raise Exception('Action (id = %i) was not found' % iden)

    def _gaa(self):
        '->Act or None. Get active action'
        for a in self.acts:
            if a.is_on():
                return a
        else:
            return None

    def name(self, iden):
        '->str. Get action name by id'
        return self._gai(iden).name

    def priority(self, iden):
        '->float. Get action priority by id'
        return self._gai(iden).current_priority()

    def weight(self, iden):
        '->float. Get action weight = priority/sum of all priorities'
        s = 0
        for a in self.acts:
            if a.is_alive():
                s += a.current_priority()
        if s == 0:
            return 0
        else:
            return self._gai(iden).current_priority() / s

    def created(self, iden):
        '->datetime. Creation time'
        return self.int_to_time(self._gai(iden).created)

    def finished(self, iden):
        '->datetime or None. Finish time'
        a = self._gai(iden)
        return None if a.is_alive() else self.int_to_time(a.finished)

    def is_on(self, iden):
        '->bool. If action (by id) is active'
        return self._gai(iden).is_on()

    def turn_on(self, iden):
        'Turn action (by) on. And Turn off all others'
        aa = self._gaa()
        if aa:
            if aa.iden == iden:
                return
            aa.switch()
        self._gai(iden).switch()
        self.write_data()
        self.emitter.emit('ActiveTaskChanged', self._gaa().iden)

    def turn_off(self):
        'Stop active action'
        aa = self._gaa()
        if aa:
            aa.switch()
        self.write_data()
        self.emitter.emit('ActiveTaskChanged')

    def finish(self, iden):
        'Finish action'
        a = self._gai(iden)
        if a.current_priority() != 0:
            a.set_priority(0)
        if a.is_on():
            a.switch()
        a.finished = self.curtime_to_int()
        self.write_data()

    def remove(self, iden):
        'Completely remove action'
        a = self._gai(iden)
        self.acts.remove(a)
        self.write_data()

    def get_weights_fun(self, t0, t1):
        """ ->{iden: PieceWiseFun}
            Calculates weight functions for all activities
            at given time interval
        """
        ftmp = [a.prior_pw(t0, t1) for a in self.acts]
        sumfun = bproc.PieceWiseFun.func(lambda *x: sum(x), *ftmp)

        ret = {}
        for a, f in zip(self.acts, ftmp):
            ret[a.iden] = bproc.PieceWiseFun.func(lambda x, y: x / y,
                    f, sumfun)
        return ret

    def get_work_fun(self, t0, t1):
        """ ->{iden: PieceWiseFun}
            Calculates work piecewise functions for all activities
            at given time interval
            key = -1 returns total work
        """
        ret = {a.iden: a.work_pw(t0, t1) for a in self.acts}
        ret[-1] = bproc.PieceWiseFun.func(lambda *x: 1, *ret.values())
        return ret

    def get_stat(self, iden, dur, endtm=None):
        """(int iden, int dur, int endtm) ->
                (int theor_time, real_time)
           Calculate time staticstics
           for time interval (endtm - dur, endtm).
           If endtm=None => endtm=CurTime
           Returns:
            theor_time (s) - time duration which current
               activity should last
            real_time (s) - time duration which current
               activity lasted in fact
        """
        a = self._gai(iden)
        t1 = self.curtime_to_int() if endtm is None else endtm
        t0 = t1 - dur
        rt = a.dur_within(t0, t1)

        pw_weights = self.get_weights_fun(t0, t1)
        pw_works = self.get_work_fun(t0, t1)

        r = bproc.PieceWiseFun.func(lambda x, y: x * y,
                pw_weights[iden], pw_works[-1])
        tt = r.integral()

        return (tt, rt)

    def get_cur_ses_time(self, iden):
        """ Returns:
                None for inactive tasks
                time duration in seconds of current duration for active
        """
        a = self._gai(iden)
        if a.is_on():
            return self.curtime_to_int() - a.onoff[-1]
        else:
            return None

if __name__ == "__main__":
    pass
