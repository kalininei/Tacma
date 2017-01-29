import os.path
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
import tacmaopt
import bproc
from tacmastat import TacmaStat
import copy


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
        # Piecewise representation off priority and onoff
        # They should be actualized at each self.prior, self.onoff changes
        # Global actualization is done by self._pw_actualize call
        self._pw_prior = bproc.PieceWiseFun([
            (self.created, float('inf'), prior)])
        self._pw_onoff = bproc.PieceWiseFun()

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

    def get_prior_pw(self, t0=None, t1=None):
        """->PieceWiseFun.
            Returns priority as a piecewise function at given interval'
            if t0, t1 = None => t0, t1 = +-Infinity
        """
        if t0 is None:
            t0 = -float('inf')
        if t1 is None:
            t1 = float('inf')
        return self._pw_prior.cut(t0, t1)

    def get_work_pw(self, t0=None, t1=None):
        """->PieceWiseFun.
            Returns activity as a piecewise function at given interval'
            if t0, t1 = None => t0, t1 = +-Infinity
        """
        if len(self.onoff) == 0:
            return bproc.PieceWiseFun()
        if t0 is None:
            t0 = -float('inf')
        if t1 is None:
            t1 = float('inf')
        return self._pw_onoff.cut(t0, t1)

    def switch(self):
        'swithes on/off status'
        self.onoff.append(self.dt.curtime_to_int())
        _d = 1 if self.is_on() else None
        self._pw_onoff.add_section(self.onoff[-1], float('inf'), _d)

    def set_priority(self, p):
        'sets new priority'
        if self.is_alive():
            self.prior.append((self.dt.curtime_to_int(), p))
            self._pw_prior.add_section(self.prior[-1][0], float('inf'), p)

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

        ret._pw_actualize()
        return ret

    def _pw_actualize(self):
        # onoff
        self._pw_onoff.clear()
        it = iter(self.onoff)
        for x1, x2 in zip(it, it):
            self._pw_onoff.add_section(x1, x2, 1)
        if self.is_on():
            self._pw_onoff.add_section(self.onoff[-1], float('inf'), 1)
        # priority
        self._pw_prior.clear()
        for x in self.prior:
            self._pw_prior.add_section(x[0], float('inf'), x[1])

    def _cutonoff(self, tm):
        ionoff = 0
        while ionoff < len(self.onoff) and self.onoff[ionoff] < tm:
            ionoff += 1
        if ionoff % 2 == 1:
            self.onoff.insert(ionoff, tm)
            self.onoff.insert(ionoff, tm)
            ionoff += 1
        return ionoff

    def _cutprior(self, tm):
        ipri = 0
        while ipri < len(self.prior) and self.prior[ipri][0] < tm:
            ipri += 1
        if ipri < len(self.prior) and self.prior[ipri][0] == tm:
            return ipri
        if ipri > 0:
            self.prior.insert(ipri, copy.deepcopy(self.prior[ipri - 1]))
        return ipri

    def delete_before(self, tm):
        # onoff
        self.onoff = self.onoff[self._cutonoff(tm):]
        # priority
        self.prior = self.prior[self._cutprior(tm):]
        self._pw_actualize()

    def delete_after(self, tm):
        if self.created >= tm:
            self.onoff = []
            self.prior = []
            return False
        if self.finished is not None and self.finished >= tm:
            self.finished = None
        # onoff
        self.onoff = self.onoff[:self._cutonoff(tm)]
        # priority
        self.prior = self.prior[:self._cutprior(tm)]
        self._pw_actualize()
        return True

    def shift_time(self, delta):
        self.onoff = [x + delta for x in self.onoff]
        self.prior = [(max(0, x[0] + delta), x[1]) for x in self.prior]
        self.created += delta
        if self.finished is not None:
            self.finished += delta
        self._pw_actualize()


class DataChangedEmitter(object):
    """
    TacmaData emits signal on events.
    Registered function should be of type: (str event, int iden)
    Events and iden list:
        'Read', iden = None. on TacmaData was read from file
        'ActiveTaskChanged', iden = new active task or None
        'NewTask', iden = identifier of a new task
        'RemoveTask', iden = identifier of removed task
        'PriorityChanged', iden = identifier task with changed prior
        'NameChanged'
        'CommentChanged'
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
        self.previous_fn = None  # previous data file
        # Build statistic object before data read
        self.stat = TacmaStat(self)

        try:
            self._read_data(self.fname)
        except Exception as e:
            print str(e)
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
            a = QtWidgets.QMessageBox.question(
                None, "Tacma Error",
                txt, QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
            if a == QtWidgets.QMessageBox.No:
                quit()
            else:
                self._read_data(None)

    def _read_data(self, fn):
        'reads data from fn if it exists or creates default data list'
        if fn is None:
            self.start_date = datetime.utcnow()
        else:
            root = ET.parse(fn).getroot()
            # read start date
            a = ['YEAR', 'MONTH', 'DAY', 'HOUR', 'MIN', 'SEC']
            a = map(lambda x: int(root.find('START_DATE/%s' % x).text), a)
            self.start_date = datetime(*a)
            # read previous archive
            try:
                self.previous_fn = root.find("PREV_DATA").text
            except:
                pass
            # read actions
            self.acts = map(lambda x: Act.read_from_xml(x, self),
                            root.findall('ACTIONS/ACTION'))
            # turn off active action
            sd = int(root.find('SAVE_TIME').text)
            aa = self._gaa()
            if aa:
                aa.onoff.append(sd)
        try:
            self.emitter.emit('Read')
        except:
            import traceback
            traceback.print_exc()

    def archivate_if_needed(self, curtime):
        # if no need for achivating return
        if curtime < tacmaopt.opt.archivate * 7 * 24 * 60 * 60:
            return curtime
        # start archivation
        afn = tacmaopt.opt.new_archive_filename()
        print "Archivating to ", afn
        # stop active task
        atask = self._gaa()
        if atask is not None:
            atask.switch()
        # calculate time interval which will be left
        delta = tacmaopt.opt.minactual * 7 * 24 * 60 * 60
        # create archive copy
        ac = copy.deepcopy(self)
        ac.delete_after(curtime - delta)
        for a in ac.acts:
            a.comment = ''
        ac.write_data(afn)
        # modify self
        self.delete_before(curtime - delta)
        self.previous_fn = afn
        # turn on active process
        if atask is not None:
            atask.switch()
        return delta

    def write_data(self, fn=None):
        tm = self.time_to_int(datetime.utcnow())
        # check for archivation only in regular saves
        if fn is None:
            tm = self.archivate_if_needed(tm)
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
        #previous data
        if self.previous_fn is not None:
            ET.SubElement(root, 'PREV_DATA').text = self.previous_fn
        #save date
        ET.SubElement(root, 'SAVE_TIME').text = str(tm)

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
        'calendar utc time to number of seconds since creation'
        delta = tm - self.start_date
        return delta.days * 86400 + delta.seconds

    def curtime_to_int(self):
        'current utc time to number of seconds since creation'
        return self.time_to_int(datetime.utcnow())

    def int_to_time(self, s):
        '-> datatime. Number of seconds to utc time'
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
        'adds task. Returns its identifier'
        iden = self._next_iden()
        self.acts.append(Act(iden, name, prior, self))
        if comment != '':
            self.set_comment(iden, comment)
        self.write_data()
        self.emitter.emit('NewTask', iden)
        return iden

    def act_count(self):
        'number of actions'
        return len(self.acts)

    def change_action_name(self, iden, newname):
        a = self._gai(iden)
        if a.name != newname:
            a.name = newname
            self.write_data()
            self.emitter.emit('NameChanged', iden)

    def change_action_prior(self, iden, newprior):
        a = self._gai(iden)
        if a.current_priority() != newprior:
            a.set_priority(newprior)
            self.write_data()
            self.emitter.emit('PriorityChanged', iden)

    def set_comment(self, iden, txt):
        if self._gai(iden).comment != txt:
            self._gai(iden).comment = txt
            self.write_data()
            self.emitter.emit('CommentChanged', iden)

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

    def created_time(self, iden):
        '->datetime. Creation time'
        return self.int_to_time(self._gai(iden).created)

    def finished_time(self, iden):
        '->datetime or None. Finish time'
        a = self._gai(iden)
        return None if a.is_alive() else self.int_to_time(a.finished)

    def is_on(self, iden):
        '->bool. If action (by id) is active'
        return self._gai(iden).is_on()

    def active_task(self):
        '->int. Get identifier of active task or None'
        at = self._gaa()
        return at.iden if at is not None else None

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
        'Stop active task'
        aa = self._gaa()
        if aa:
            aa.switch()
        self.write_data()
        self.emitter.emit('ActiveTaskChanged')

    def finish(self, iden):
        'Finish task'
        a = self._gai(iden)
        if a.current_priority() != 0:
            a.set_priority(0)
        if a.is_on():
            a.switch()
        a.finished = self.curtime_to_int()
        self.write_data()

    def remove(self, iden):
        'Completely remove task from all statistics'
        a = self._gai(iden)
        self.acts.remove(a)
        self.write_data()
        self.emitter.emit('RemoveTask', iden)

    def delete_before(self, tm):
        """ deletes all data before tm
        """
        # acts
        for a in self.acts:
            a.delete_before(tm)
            a.shift_time(-tm)
        # curtime
        self.start_date = self.int_to_time(tm)
        # reset stat
        self.stat._aux_reset()

    def delete_after(self, tm):
        """ deletes all data after tm
        """
        rmtasks = []
        for a in self.acts:
            need = a.delete_after(tm)
            if not need:
                rmtasks.append(a)
        for r in rmtasks:
            self.acts.remove(r)
        # reset stat
        self.stat._aux_reset()


if __name__ == "__main__":
    pass
