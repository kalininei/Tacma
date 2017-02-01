import bproc
import copy
import xml.etree.ElementTree as ET


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
        self.archived_stop = self.created
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
        ET.SubElement(d, 'ARCHIVED_STOP').text = str(self.archived_stop)

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
            try:
                fnd = nd.find('ARCHIVED_STOP')
                ret.archived_stop = int(fnd.text)
            except:
                ret.archived_stop = ret.created
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

    def last_stop(self):
        """ Returnss ending time of last
            session lasting more than 5 minutes if inactive.
            None otherwise
        """
        if self.is_on():
            return None
        for i, tm in enumerate(reversed(self.onoff)):
            if i % 2 == 0:
                last_end = tm
                continue
            dur = last_end - tm
            if dur > 300:
                return last_end
        return self.archived_stop

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
        self.archived_stop += delta
        if self.finished is not None:
            self.finished += delta
        self._pw_actualize()
