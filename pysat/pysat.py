#!/usr/bin/python
"""
Python Sat Solver

To use simply, $ python -OO {this} {cnf file}
OO option is optimize option.
"""
import logging

if __debug__:
    logging.basicConfig(level=logging.DEBUG)


class Solver(object):
    """
    Solver object
    """
    def __init__(self):
        self.litlist = LitList()
        self.clause_list = []
        self.learnt_list = []

        self.level = 0
        self.root_level = 0

        # key -> level, value -> literal list
        self.propagate_history = {}
        self.decide_history = {}

        # True  -> satisfied
        # False -> unsatisfied
        # None  -> running
        self.status = None

        self.conflict_count = 0
        self.decide_count = 0

        # sign when literal decided.
        self.ASSIGN_DEFAULT = True

    def solve(self):
        """start solving

        try solving while unsat or sat
        """
        logging.debug("solve")
        logging.info(str(self))
        while self.is_running():
            self._solve()

    def _solve(self):
        """main solving function

        Returns:
            None
        """
        while True:
            conflict_clause = self.propagate()
            if isinstance(conflict_clause, Clause):
                self.conflict_count += 1
                if self.level == self.root_level:
                    # CONTRADICTION
                    self.status = False
                    return
                backjump_level, learnt_clause = self.analyze(conflict_clause)
                self.add_clause(learnt_clause)
                self.cancel_until(backjump_level)
                self.level = backjump_level
            else:
                self.decide_count += 1

                # restart here
                if self.decide_count % 1000 == 0:
                    save_result(self)

                # NO CONFLICT
                next_lit = self.popup_literal()
                if next_lit is None:
                    # ALL ASSIGNED, SATISFIED
                    self.status = True
                    return
                else:
                    self.decide(next_lit)

        pass

    def propagate(self):
        """

        Returns:
            (backjump_level, learnt_clause)
        """
        while True:
            propagatable_list = []
            # reloading watching ltieral
            for c in self.clause_list+self.learnt_list:
                tmp = c.reload_watching_literal()
                if tmp is True:
                    continue
                elif isinstance(tmp, BindLit):
                    propagatable_list.append((tmp,c))
                elif tmp is False:
                    return c

            if len(propagatable_list) == 0:
                return None

            #propagate literals
            for blit, reason in propagatable_list:
                sign = blit.get_raw_sign()
                blit.lit.assign(sign,self.level,reason)
                if self.level != 0:
                    self.propagate_history[self.level].append(blit)

    def analyze(self, conflict_clause):
        """analyze conflicting clause

        returns learnt clause

        :param conflict_clause: conflicting clause
        :type conflict_clause: Clause
        :returns: (int, Clause) -- (backjump_level, learnt_clause)
        """
        LIT_HISTORY = [self.decide_history[self.level]]+[x.lit for x in self.propagate_history[self.level]]
        def _pop_next_pointer(blit_set):
            """return latest literal

            :returns: (Lit, list) -- (next_literal, bind_literal_list)
            """
            data = [x.lit for x in blit_set]
            for lit in reversed(LIT_HISTORY):
                if lit in data:
                    others = [x for x in blit_set if lit is not x.lit]
                    return lit, others
            assert False, "not reachable"

        logging.debug(self)

        logging.info("analyze %s"%str(conflict_clause))
        logging.info("level %d %s"%(self.level, self.decide_history[self.level]))
        logging.info("propagate_history lv.%d: %s"%(self.level,', '.join([str(x)for x in self.propagate_history[self.level]])))

        lower_level_blit = set()
        current_level_blit = set()
        done_lit = set()
        pool_blit = [x for x in conflict_clause.get_bindlit_list()]

        while True:
            #SEPARATING
            for blit in pool_blit:
                assert blit.lit.get_level() <= self.level, "future level is reachable"
                if blit.lit.get_level() == self.level:
                    current_level_blit.add(blit)
                else:
                    lower_level_blit.add(blit)

            # if you need simplify blit list, write here.

            logging.debug('done: '+', '.join([str(x.id) for x in done_lit]))
            logging.debug('pool: '+', '.join([str(x) for x in pool_blit]))
            logging.debug('lower: '+', '.join([str(x) for x in lower_level_blit]))
            logging.debug('current: '+', '.join([str(x) for x in current_level_blit]))
            assert len(current_level_blit) >= 1, "arienai"
            if len(current_level_blit) == 1:
                # find UIP
                break

            head_lit, tail_blit = _pop_next_pointer(current_level_blit)

            done_lit.add(head_lit)
            pool_blit = set([x for x in head_lit.get_reason().get_bindlit_list()if x.lit not in done_lit])
            current_level_blit = set(tail_blit)

        learnt_list = [x.lit for x in list(current_level_blit) + list(lower_level_blit)]
        if lower_level_blit:
            backjump_level = max([x.lit.get_level()for x in lower_level_blit])
        else:
            backjump_level = self.level-1
        learnt_clause = self._gen_learnt_clause(learnt_list)
        return backjump_level, learnt_clause

    def _gen_learnt_clause(self, lit_list):
        """generate learnt clause from literal list.

        :param lit_list: literal list
        :type lit_list: list
        """
        blit_list = []
        for lit in lit_list:
            sign = lit.get_sign()
            assert isinstance(sign, bool), 'unassigned is arienai %s'%sign
            blit_list.append(lit.get_bind_lit(not sign))
        return Clause(blit_list, learnt=True)

    def cancel_until(self, backjump_level):
        """rollback to backjump_level

        :param backjump_level: backjump level
        :type backjump_level: int
        :returns: None
        """
        keys = list(self.decide_history.keys())
        for key in keys:
            if key > backjump_level:
                del self.propagate_history[key]
        for key in keys:
            if key > backjump_level:
                del self.decide_history[key]
        for lit in self.litlist:
            if not lit.is_unassigned() and (lit.get_level() > backjump_level):
                lit.set_default()

    def decide(self, lit):
        """decide literal as ASSIGN_DEFAULT

        :param lit: decide literal
        :type lit: Lit
        :returns: None
        """
        assert isinstance(lit, Lit)
        self.level += 1
        lit.assign(self.ASSIGN_DEFAULT, self.level)
        self.decide_history[self.level] = lit
        self.propagate_history[self.level] = []
        logging.info('decide: %s'%lit)
        logging.debug(str(self))

    def add_clause(self, clause):
        """add clause to solver

        if one literal clause is given,
            assign literal without adding solver's clause list.
        if learnt clause is given, add learnt clause list.

        :param clause: clause
        :type clause: Clause
        :returns: None
        """
        assert isinstance(clause, Clause)
        if len(clause) == 1:
            blit = clause.get_bindlit_list()[0]
            sign = blit.get_raw_sign()
            blit.lit.assign(sign, self.root_level)
            return
        clause.set_watching_literal((0,1))
        if clause.is_learnt():
            self.learnt_list.append(clause)
        else:
            self.clause_list.append(clause)

    def popup_literal(self, is_random=True):
        """select next decide literal from unassigned literal.

        :param is_random: optional default is True
        :type is_random: bool
        :returns: None
        """
        if is_random:
            import random
            l = [x for x in self.litlist if x.is_unassigned()]
            if len(l) == 0:
                return None
            else:
                i = random.randint(0,len(l)-1)
                return l[i]
        else:
            for lit in self.litlist:
                if lit.is_unassigned():
                    return lit
            return None

    def print_result(self):
        """print status
        """
        if self.status is True:
            print("")
            print("#############")
            print("#satisfied!!#")
            print("#############")
            print("")
        elif self.status is False:
            print("")
            print("-------------")
            print("-Unsatisfied-")
            print("-------------")
            print("")

    def is_running(self):
        return self.status is None

    def is_sat(self):
        return self.status is True

    def _str_history(self):
        string = ""
        for key in sorted(self.propagate_history.keys()):
            line = self.propagate_history[key]
            lit = self.decide_history[key]
            string += 'lv.%03d '%key
            string += '% 7d: '%lit.get_id()
            string += ', '.join([str(x)for x in line])
            string += '\n'
        return string

    def __str__(self):
        string = "###############level:%d root_level:%d\n"%(self.level, self.root_level)
        string += "####Literals\n"+"\n".join([str(x)for x in self.litlist])
        string += "\n\n"
        string += "####Clauses\n"+"\n".join([str(x)for x in self.clause_list])
        string += "\n\n"
        string += "####Learnts\n"+"\n".join([str(x)for x in self.learnt_list])
        string += "\n\n"
        string += "####Tree\n"
        string += self._str_history()
        return string


class Lit(object):
    def __init__(self, id):
        self.id = id
        self.bindlits = self._gen_bindlit()
        self.set_default()

    def assign(self, sign, level, reason=None):
        assert isinstance(sign, bool)
        assert isinstance(level, int)
        assert reason is None or isinstance(reason, Clause)
        self.sign = sign
        self.level = level
        self.reason = reason

    def set_default(self):
        self.sign = None
        self.level = None
        self.reason = None

    def get_sign(self):
        return self.sign

    def get_bind_lit(self, sign):
        assert isinstance(sign, bool)
        return self.bindlits[sign]

    def get_id(self):
        return self.id

    def get_reason(self):
        return self.reason

    def get_level(self):
        return self.level

    def is_unassigned(self):
        return self.sign is None

    def _gen_bindlit(self):
        res = {}
        res[True] = BindLit(self, True)
        res[False] = BindLit(self, False)
        return res

    def __str__(self):
        return "{var:10d}:{level}-{sign}{propagated}".format(
            var=self.get_id(),
            sign="unassigned" if self.sign is None else self.sign,
            propagated= "-propagated"+str(self.reason.id) if self.get_reason()else "",
            level=self.level
        )



class LitList(object):
    def __init__(self):
        self.data = []
        pass
    def get(self, id):
        assert isinstance(id, int)
        idx = abs(id)
        assert idx >= 1
        if len(self.data) < idx:
            self._gen_lit(idx)
        return self.data[idx-1]

    def get_bind_lit(self, id):
        lit = self.get(id)
        if id < 0:
            return lit.get_bind_lit(False)
        else:
            return lit.get_bind_lit(True)

    def _gen_lit(self, num):
        while len(self.data) < num:
            next_id = len(self.data)+1 # for 1-index
            self.data.append(Lit(next_id))

    def __iter__(self):
        return iter(self.data)


class Clause(object):
    """
    """
    _num = 0
    # self.id : int
    # self.learnt : bool

    def __init__(self, bindlit_list, learnt=False):
        assert isinstance(learnt, bool)
        self.id = self._gen_id()
        self.bindlit_list = sorted(bindlit_list,key=lambda y:y.lit.get_id())
        self.learnt = learnt
        self.watching_literal = None
        pass

    def reload_watching_literal(self):
        """
        reload successful, return True
        propagatable, return bindlit
        conflict return False
        """
        res = self._check_watching_literal()
        for i, idx in enumerate(res):
            if idx is None:
                for new_idx, blit in enumerate(self.bindlit_list):
                    if (blit.get_sign() is not False) and (new_idx not in res):
                        res[i] = new_idx
        assert len(res) == 2
        c = res.count(None)
        if c == 0:
            #ok
            self.set_watching_literal(tuple(res))
            return True
        elif c == 1:
            #propagatable
            idx = [x for x in res if x is not None][0]
            propagatable_blit = self.bindlit_list[idx]
            if propagatable_blit.get_sign() is None:
                # UNASSIGNED
                return propagatable_blit
            else:
                # ASSIGNED TRUE
                return True
        elif c == 2:
            #conflict
            return False
        assert False, "not reachable"

    def set_watching_literal(self, wl):
        assert isinstance(wl, tuple)
        assert None not in wl, str(wl)
        assert len(wl) == 2, str(wl)
        assert all([isinstance(x,int)for x in wl]), str(wl)
        self.watching_literal = wl

    def get_bindlit_list(self):
        return self.bindlit_list

    def is_learnt(self):
        return self.learnt is True

    def _check_watching_literal(self):
        return [None if self.bindlit_list[x].get_sign()is False else x for x in self.watching_literal]

    @classmethod
    def _gen_id(cls):
        cls._num += 1
        return cls._num

    def __len__(self):
        return len(self.bindlit_list)

    def __str__(self):
        return "{id:3d} :{watching}:{learnt}: {lits}".format(
            id=self.id,
            watching=self.watching_literal,
            lits=", ".join([str(x)for x in self.bindlit_list]),
            learnt="l"if self.learnt else "-"
        )


class BindLit(object):
    def __init__(self, lit, sign):
        self.lit = lit
        self._sign = sign

    def get_sign(self):
        s = self.lit.get_sign()
        if s is None:
            return None
        elif self._sign:
            return s
        else:
            return not s

    def get_raw_sign(self):
        return self._sign

    def __str__(self):
        if self._sign:
            return " %2d"%self.lit.get_id()
        else:
            return "-%2d"%self.lit.get_id()


def parse(string):
    import re

    solver = Solver()
    def parse_clause(inp):
        s = set()
        for x in inp.split(' '):
            if x == '':
                continue
            elif x == '0':
                break

            try:
                num = int(x)
            except ValueError:
                continue

            s.add(num)
        if len(s) == 0:
            return
        bll = [solver.litlist.get_bind_lit(x)for x in s]
        return Clause(bll)
    pat = re.compile('\A[^pc]+')
    for line in string.splitlines():
        c_result = pat.search(line)
        if c_result is None:
            continue
        clause = parse_clause(c_result.group())
        if clause:
            solver.add_clause(clause)
    return solver

def save_result(solver):
    string = str(solver)
    with open("/tmp/resutlt",'w') as fp:
        fp.write(string)

def usage():
    print("Usage: {cmd} cnffile".format(cmd=__file__))

if __name__ == '__main__':
    import sys
    if len(sys.argv) == 2:
        string = open(sys.argv[1]).read()
        solver = parse(string)
        print(solver)
        solver.solve()
        print(solver)
        solver.print_result()
        save_result(solver)
        if solver.status == False:
            sys.exit(1)
    else:
        usage()
    pass
