import bproc


class TacmaStat(object):
    'Computes statistics on TacmaData'
    def __init__(self, dt):
        ' dt - TacmaData object'
        self._dt = dt
        self._dt.emitter.subscribe(self, self._data_changed)

        # --- Auxilliary data sets are modifyed during data_changed events
        self._aux_init()

    def last_session(self, iden):
        """ Returns:
                duration of last session if this task is active or
                has largest end time.
                None otherwise
        """
        task = self._dt._gai(iden)
        act_iden = self._dt.active_task()
        if act_iden is not None:
            if iden == act_iden:
                return self._dt.curtime_to_int() - task.onoff[-1]
            else:
                return None
        else:
            iden_last, time_last, dur = None, 0, None
            for a in self._dt.acts:
                if len(a.onoff) > 0 and a.onoff[-1] > time_last:
                    iden_last, time_last = a.iden, a.onoff[-1]
                    dur = a.onoff[-1] - a.onoff[-2]
            if iden_last == iden:
                return dur
            else:
                return None

    def must_time(self, iden, dur, endtm=None):
        """ ->int.
        Get duration which this task should occupy within
        [endtm - dur, endtm] time interval
        endtm=None -> endtm = current time
        """
        t1 = self._dt.curtime_to_int() if endtm is None else endtm
        t0 = max(0, t1 - dur)
        return self._working_portion[iden].integral(t0, t1)

    def real_time(self, iden, dur, endtm=None):
        """ ->int.
        Get duration which this task occupied within
        [endtm - dur, endtm] time interval
        endtm=None -> endtm = current time
        """
        task = self._dt._gai(iden)
        t1 = self._dt.curtime_to_int() if endtm is None else endtm
        t0 = max(0, t1 - dur)
        return task.dur_within(t0, t1)

    def _data_changed(self, event, iden):
        # TODO: this could be optimized
        # Now it simply rebuilds all auxilliary data
        # on every change
        if event in ['NameChanged', 'CommentChanged']:
            return
        self._aux_reset()

    def _aux_init(self):
        ' all auxilliary data to zero'
        # PieceWiseFun. Total working activity. Equals 1 if any task was
        # active
        self._working_activity = bproc.PieceWiseFun()

        # {identifier -> PieceWiseFunc} Represents weigth [0, 1] of a task
        # on a time line
        self._weights = {}

        # {identifier -> PieceWiseFunc} Represents weigth [0, 1] of a task
        # multiplied by total working activity
        self._working_portion = {}

    def _aux_reset(self):
        ' Reset working_activity, weights, workting portion'
        self._aux_init()
        d = self._dt
        if d.act_count() == 0:
            return

        # 1. weights
        # Non normalised priorities
        ftmp = [a.get_prior_pw() for a in d.acts]
        # Sum of all priorities
        sumfun = bproc.PieceWiseFun.func(lambda *x: sum(x), *ftmp)
        # Normalize priorities to get weights
        for a, f in zip(d.acts, ftmp):
            self._weights[a.iden] = bproc.PieceWiseFun.func(
                lambda x, y: x / y, f, sumfun)

        # 2. total working activity
        # activity for each task
        ftmp = [a.get_work_pw() for a in d.acts]
        # place 1 if any activity is 1
        self._working_activity = \
            bproc.PieceWiseFun.func(lambda *x: 1, *ftmp)

        # 3. working portion = weights * working_activity
        self._working_portion = {a.iden: bproc.PieceWiseFun.func(
            lambda x, y: x * y, self._weights[a.iden], self._working_activity)
            for a in d.acts}
