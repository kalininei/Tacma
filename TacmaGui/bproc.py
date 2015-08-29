
def resfile(fname):
    'get file from resources'
    import os.path
    return os.path.join(os.path.dirname(__file__), fname)


_icon_set = {}


def get_icon(s):
    from PyQt5 import QtGui
    """ ->QtGui.QIcon. Returns icon by its string code:
            tacma
    """
    global _icon_set
    if len(_icon_set) == 0:
        _icon_set = {
                "tacma":
                QtGui.QIcon(QtGui.QPixmap(resfile('misc/mainwin.png'))),
                "icon-run":
                QtGui.QIcon(QtGui.QPixmap(resfile('misc/icon_run.png'))),
                "icon-stop":
                QtGui.QIcon(QtGui.QPixmap(resfile('misc/icon_stop.png'))),
        }
    return _icon_set[s]


#xml indent
def xmlindent(elem, level=0):
    """ http://effbot.org/zone/element-lib.htm#prettyprint.
        It basically walks your tree and adds spaces and newlines so the tree i
        printed in a nice way
    """
    tabsym = "  "
    i = "\n" + level * tabsym
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + tabsym
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for elem in elem:
            xmlindent(elem, level + 1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i


class PieceWiseFun(object):
    def __init__(self, dt=None, boundto=None):
        """ dt -- [(tstart, tend, value), ....]
            boundto -- [t0, t1]  - bounds data to this interval
        """
        self._dt = []
        if dt is not None:
            for d in dt:
                self.add_section(d[0], d[1], d[2], boundto)

    def add_section(self, tstart, tend, value, boundto=None):
        """ Adds section [tstart, tend] with value
            boundto -- [t0, t1]  - bounds data to this interval
            if value=None -> simply removes this section from data
        """
        tstart, tend = float(tstart), float(tend)
        if boundto is not None:
            tstart = max(tstart, boundto[0])
            tend = min(tend, boundto[1])
        if tend <= tstart:
            return
        if value is not None:
            newdt = [(tstart, tend, value)]
        else:
            newdt = []
        for d in self._dt[:]:
            if d[0] >= tend or d[1] <= tstart:
                newdt.append(d)
            elif d[0] < tstart < d[1] and d[1] < tend < d[1]:
                newdt.append((d[0], tstart, d[2]))
                newdt.append((tend, d[1], d[2]))
            elif d[0] >= tstart and d[1] <= tend:
                continue
            elif d[0] < tend < d[1]:
                newdt.append((tend, d[1], d[2]))
            elif d[0] < tstart < d[1]:
                newdt.append((d[0], tstart, d[2]))
        newdt.sort(key=lambda x: x[0])
        self._dt = newdt

    def clear(self):
        " removes all information "
        self._dt = []

    def cut(self, tstart, tend):
        """ -> PieceWiseFun
            Returns function which equals present on interval [t0, t1]
            and zero outside it.
        """
        ret = PieceWiseFun()
        for d in self._dt:
            if d[1] <= tstart:
                continue
            elif d[0] >= tend:
                break
            elif tstart <= d[0] <= tend and tstart <= d[1] <= tend:
                ret._dt.append((d[0], d[1], d[2]))
            elif d[0] <= tstart and d[1] >= tend:
                ret._dt.append((tstart, tend, d[2]))
            elif d[0] < tstart:
                ret._dt.append((tstart, d[1], d[2]))
            elif d[1] > tend:
                ret._dt.append((d[0], tend, d[2]))

        return ret

    def boundaries(self):
        """ -> (t0, t1).
            Returns lowest and largest coordinate value
            None if secnum() == 0
        """
        if self.secnum() == 0:
            return None
        else:
            return (self._dt[0][0], self._dt[-1][1])

    def secnum(self):
        return len(self._dt)

    def ip0(self, i):
        return self._dt[i][0]

    def ip1(self, i):
        return self._dt[i][1]

    def iv(self, i):
        return self._dt[i][2]

    def val(self, t):
        for d in self._dt:
            if t >= d[0] and t < d[1]:
                return d[2]
        if t == float('inf'):
            if self.secnum() > 0 and t == self._dt[-1][1]:
                return self._dt[-1][2]
        return 0

    def integral(self, t0=None, t1=None):
        '->float. Computes integral on given segment'
        if self.secnum() == 0:
            return 0
        ret = 0
        t0 = self._dt[0][0] if t0 is None else t0
        t1 = self._dt[-1][1] if t1 is None else t1
        for d in self._dt:
            if t1 <= d[0]:
                break
            elif t0 >= d[1]:
                continue
            elif d[0] <= t0 <= d[1] and d[0] <= t1 <= d[1]:
                ret += (t1 - t0) * d[2]
            elif t0 <= d[0] and t1 >= d[1]:
                ret += (d[1] - d[0]) * d[2]
            elif d[0] < t1 < d[1]:
                ret += (t1 - d[0]) * d[2]
            elif d[0] < t0 < d[1]:
                ret += (d[1] - t0) * d[2]

        return ret

    def __str__(self):
        ret = ''
        for d in self._dt:
            ret += '[%s, %s] -- %s' % (str(d[0]), str(d[1]), str(d[2]))
            ret += '\n'
        return ret

    @classmethod
    def func(cls, fun, *args):
        """ ((x0, x1, ..)->float, (PieceWiseFun)) -> PieceWiseFun
            Build a new PieceWiseFun from combination of others
            Example. Sum:
                f1 = PieceWiseFun(...)
                f2 = PieceWiseFun(...)
                f3 = PieceWiseFun.func(lambda x, y: x + y, f1, f2)
        """
        ret = cls()
        if len(args) == 0:
            return ret
        f = cls._same_stencil(args)
        for i, d in enumerate(f[0]._dt):
            t1, t2 = d[0], d[1]
            vals = [x._dt[i][2] for x in f]
            v = fun(*vals)
            ret.add_section(t1, t2, v)
        ret._simplify_stencil()
        return ret

    @classmethod
    def _same_stencil(cls, fun):
        '-> [cls]. decomposes fun[0], fun[1], ... to same partition'
        c = set()
        for f in fun:
            for d in f._dt:
                c.add(d[0])
                c.add(d[1])
        c = sorted(c)
        ret = [cls() for i in range(len(fun))]

        for i in range(len(c) - 1):
            t0, t1 = c[i], c[i + 1]
            tav = (t0 + t1) / 2.0
            v = [f.val(tav) for f in fun]
            if not all(map(lambda x: x == 0, v)):
                for i in range(len(fun)):
                    ret[i].add_section(t0, t1, v[i])
        return ret

    def _simplify_stencil(self):
        'simplifies stencil'
        # remove zeros
        self._dt = filter(lambda x: x[2] != 0, self._dt)
        if self.secnum() == 0:
            return
        # union segments with same values
        newdt = [self._dt[0]]
        for d in self._dt[1:]:
            if d[2] != newdt[-1][2] or d[0] != newdt[-1][1]:
                newdt.append(d)
            else:
                newdt[-1] = (newdt[-1][0], d[1], d[2])
        self._dt = newdt

if __name__ == "__main__":
    A = float('inf')
    f1 = PieceWiseFun([(285, 341, 1), (341, A, 0.25)])
    sumfun = PieceWiseFun.func(lambda *x: sum(x), f1)
    [sumfun] = PieceWiseFun._same_stencil([f1])

    print f1
    print sumfun
