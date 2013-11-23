#!/usr/bin/python -OO
"""
Python Sat Solver

To use simply, $ {this} {cnf file}
or $ python -OO {cnf file}

If possible, you should use pypy.
"""
import logging
import random
import argparse
import re

RESULT_FILE = None

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
        self.pickup_type = "random"

    def solve(self):
        """start solving

        try solving while unsat or sat
        return sat or unsat as solver.status
        """
        logging.debug("solve")
        logging.info(str(self))
        while self.is_running():
            self._solve()

    def _solve(self):
        """main solving function"""
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
        """propagate clause, reloading watching literal

        Returns:
            Clause or None

            Clause : Conflicting Clause
            None   : No conflicting, propagated successfully
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

        Arguments:
            conflict_clause(Clause): conflicting clause
        Returns:
            (backjump_level, learnt_clause)

            backjump_level(int)  : backjump level
            learnt_clause(clause) : learnt clause by analyzing conflicting clause
        """

        # implication graph in the level
        LIT_HISTORY = [self.decide_history[self.level]]+[x.lit for x in self.propagate_history[self.level]]
        def _pop_next_pointer(blit_set):
            # pop latest literal on implication graph from blit_set
            #
            # Arguments:
            #   blit_set(set) : BindLit set
            # Returns:
            #   (next_literal, bind_literal_list)
            #   next_literal(Lit) : latest literal on implication graph
            #   bind_literal_list(list) : other bind literals
            data = [x.lit for x in blit_set]
            for lit in reversed(LIT_HISTORY):
                if lit in data:
                    others = [x for x in blit_set if lit is not x.lit]
                    return lit, others
            assert False, "not reachable"

        logging.debug(self)
        logging.debug("analyze %s"%str(conflict_clause))
        logging.debug("level %d %s"%(self.level, self.decide_history[self.level]))
        logging.debug("propagate_history lv.%d: %s"%(self.level,', '.join([str(x)for x in self.propagate_history[self.level]])))

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

        Arguments:
            lit_list(list) : literal list, it will convert to learnt clause
        Returns:
            learnt_clause(Clause)
        """
        blit_list = []
        for lit in lit_list:
            sign = lit.get_sign()
            assert isinstance(sign, bool), 'unassigned is arienai %s'%sign
            blit_list.append(lit.get_bind_lit(not sign))
        return Clause(blit_list, is_learnt=True)

    def cancel_until(self, backjump_level):
        """rollback to backjump_level

        Arguments:
            backjump_level(int) : rollback to the backjump level
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

    def decide(self, decide_literal):
        """decide literal as ASSIGN_DEFAULT

        Arguments:
            decide_literal(Lit)
        """
        assert isinstance(decide_literal, Lit)
        self.level += 1
        decide_literal.assign(self.ASSIGN_DEFAULT, self.level)
        self.decide_history[self.level] = decide_literal
        self.propagate_history[self.level] = []
        logging.debug('decide: %s'%decide_literal)
        logging.debug(str(self))

    def add_clause(self, clause):
        """add clause to solver

        if one literal clause is given,
            assign literal without adding solver's clause list.
        if learnt clause is given, add learnt clause list.

        Arguments:
            clause(Clause)
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

    def popup_literal(self):
        """select next decide literal from unassigned literal.
        """

        if self.pickup_type == 'random':
            # random
            l = [x for x in self.litlist if x.is_unassigned()]
            if len(l) == 0:
                return None
            else:
                i = random.randint(0,len(l)-1)
                return l[i]
        else:
            # order
            for lit in self.litlist:
                if lit.is_unassigned():
                    return lit
            return None

    def print_result(self):
        """print satisfied or unsatisfied"""
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
    """Literal Object

    Attributes:
        id(id): unique id
        bindlits(dict): the literal's bind literal, key is True or False
        sign(None or bool): literal's sign
            None -- unassigned
            True -- assigned True
            False -- assigned False
        level(int): level when assigned
        reason(None or Clause): if the literal is propagated, the reason clause
    """
    def __init__(self, id):
        """initialize literal

        Arguments:
            id: literal unique id
        """
        self.id = id
        self.bindlits = self._gen_bindlit()
        self.set_default()

    def assign(self, sign, level, reason=None):
        """assign literal

        if propagated, set reason

        Arguments:
            sign(bool): literal sign
            level(int): decide or propagated level
            reason(Clause):(optical)if propagated, the reason clause
        """
        assert isinstance(sign, bool)
        assert isinstance(level, int)
        assert reason is None or isinstance(reason, Clause)
        self.sign = sign
        self.level = level
        self.reason = reason

    def set_default(self):
        """reset to default attribute
        """
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
    """literal list

    this object is one-index list.
    so you can use literal.id and cnf number as index, when you generate this as expected.
    """
    def __init__(self):
        self.data = []
        pass
    def get(self, id):
        """get literal from list

        Arguments:
            id(int): literal id, don't mind positive or negative
        Returns:
            Lit
        """
        assert isinstance(id, int)
        idx = abs(id)
        assert idx >= 1
        if len(self.data) < idx:
            self._gen_lit(idx)
        return self.data[idx-1]

    def get_bind_lit(self, id):
        """get binded literal from list

        Arguments:
            id(int): literal id. if negative, returns False bind_lit.
        Returns:
            BindLit
        """
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
    """Clause Object

    Attributes:
        id(int): unique id
        bindlit_list(list): component bind literals
        _is_learnt(bool)
        watching_literal(tuble or None):
            None -- not initialized
            tuple(int, int) -- bindlit_list's index
    """
    _num = 0
    # self.id : int
    # self.learnt : bool

    def __init__(self, bindlit_list, is_learnt=False):
        assert isinstance(is_learnt, bool)
        self.id = self._gen_id()
        self.bindlit_list = sorted(bindlit_list,key=lambda y:y.lit.get_id())
        self._is_learnt = is_learnt
        self.watching_literal = None
        pass

    def reload_watching_literal(self):
        """reload watching literal

        Returns:
            bool or BindLit

            BindLit -- propagatable literal
            True    -- the clause is satisfied or unassigned
            False   -- conflict
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
        """
        Arguments:
            wl(tuple): (int, int) -- watching literal indexes
        """
        assert isinstance(wl, tuple)
        assert None not in wl, str(wl)
        assert len(wl) == 2, str(wl)
        assert all([isinstance(x,int)for x in wl]), str(wl)
        self.watching_literal = wl

    def get_bindlit_list(self):
        return self.bindlit_list

    def is_learnt(self):
        return self._is_learnt is True

    def _check_watching_literal(self):
        """check watching literal

        Returns:
            [int or None, int or None]
            int -- the literal index
            None -- the literal is assigned False, so the literal need reload
        """
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
            learnt="l"if self._is_learnt else "-"
        )


class BindLit(object):
    """bind literal and sign for clause

    Attributes:
        lit(Lit)
        _sign(bool)
    """
    def __init__(self, lit, sign):
        self.lit = lit
        self._sign = sign

    def get_sign(self):
        """return bindlit's sign and the literal's sign

        Returns:
            bool
        """
        s = self.lit.get_sign()
        if s is None:
            return None
        elif self._sign:
            return s
        else:
            return not s

    def get_raw_sign(self):
        """return the bindlit's sign

        Returns:
            bool
        """
        return self._sign

    def __str__(self):
        if self._sign:
            return " %2d"%self.lit.get_id()
        else:
            return "-%2d"%self.lit.get_id()


def parse(string):
    """parse string as CNF file

    Returns:
        Solver
    """
    solver = Solver()
    def parse_clause(inp):
        """parse cnf line to clause

        Arguments:
            inp(str)
        Returns:
            Clause
        """
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
    """save solver status as RESULT_FILE

    Arguments:
        solver(Solver)
    """
    string = str(solver)
    if RESULT_FILE:
        RESULT_FILE.write(string)

def argument_parse():
    parser = argparse.ArgumentParser(description="Sat Solver on Python")
    parser.add_argument('file',
                        type=open,
                        help='cnf file name',
                        )
    parser.add_argument('--choose-type',
                        choices=['random','order'],
                        help='how decide literal choose',
                        default='random',
                        )
    parser.add_argument('--assign-default',
                        type=bool,
                        help='default decide',
                        default=True
                        )
    parser.add_argument('--result-path',
                        type=open,
                        help='ouptput result path',
                        default=None,
                        )
    return parser.parse_args()

if __name__ == '__main__':
    arguments = argument_parse()
    string = arguments.file.read()
    solver = parse(string)

    solver.ASSIGN_DEFAULT = arguments.assign_default
    solver.choose_type = arguments.choose_type
    RESULT_FILE = arguments.result_path

    solver.solve()
    print(solver)

    solver.print_result()
    save_result(solver)