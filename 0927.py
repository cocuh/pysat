"""
SatSolver by python.

if you need please use with "-O" option
"""
#Solver
# |(list)
#Clause  ->
# |(List)
#BindLit -> sign
# |
#Lit
import logging
import sys
import re


if __debug__:
    logging.basicConfig(level=logging.INFO)

class UnassignedException(BaseException):pass


'''
class TypeCheckError(BaseException):pass

def type_check(argument_type_list, return_type_list):
    def _func1(function):
        def _func2(*argument):
            pass
        return function
    return _func1
'''


class Solver(object):
    """
    solver
    """

    def __init__(self):
        self._set_default()
        self.ASSIGN_DEFAULT = True

    def solve(self):
        logging.debug("solve start")
        logging.info(str(self))
        while self.is_undef():
            self._solve()
        self.print_result()

    def _solve(self):
        while True:
            conflict_clause = self._propagate()
            if conflict_clause is None:
                # NO CONFLICT
                # TODO: restart here
                self._decide_count += 1
                decide_literal = self._popup_literal()
                if decide_literal is None:
                    # STATISFIED
                    assert self.is_sat()
                    self.status = True
                    return
                else:
                    self._decide(decide_literal)
            else:
                # CONFLICT
                self._coflict_count += 1
                if self.level == self.root_level:
                    # UNSAT
                    self.status = False
                    return
                backjump_level, learnt_clause = self._analyze(conflict_clause)
                self.add_clause(learnt_clause)
                self._cancel_until(backjump_level)
                self.level = backjump_level - 1
                logging.info("search backjump to level:%d"%backjump_level)
        pass

    def print_result(self):
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

    def add_clause(self, clause):
        """
        add clause
        if one literal, decide on root_level.
        if learnt clause, add learnt_list
        others, add clause_list

        rtype: None
        """
        assert isinstance(clause, Clause)
        assert (len(clause) >= 1), str(clause)
        data = clause.get_data()
        if len(data) == 1:
            bind_lit = data[0]
            sign = bind_lit.get_raw_sign()
            bind_lit.lit.assign(sign, self.root_level)
            return
        clause.set_watching_literal((0,1))
        if clause.is_learnt():
            self.learnt_list.append(clause)
            return
        else:
            self.clause_list.append(clause)
            return

    def _cancel_until(self, level):
        """
        reset until level
        rtype: None
        """
        assert type(level) is int
        for lit in self.litlist:
            if lit.get_level() >= level:
                lit.set_default()
        for key in self.propagate_history.keys():
            if key >= level:
                del self.propagate_history[key]
        for key in self.decide_history.keys():
            if key >= level:
                del self.propagate_history[level]
        return None

    def _analyze(self, conflict_clause):
        """
        from conflict_clause, return Clause object and backjump_level

        rtype: (int,Clause)
        """
        #TODO: refactor
        def _popup_next_pointer(base_lit_list, bindlit_list):
            """
            fucntion for CDCL. searching first UIP
            return (lit, others)
             | lit -> literal
             | others -> bindlist list
            """
            data = [x.lit for x in bindlit_list]
            for lit in reversed(base_lit_list):
                if lit in data:
                    others = [x for x in bindlit_list if lit is not x.lit]
                    return lit, others

        logging.info("analyze %s"%str(conflict_clause))
        logging.info("level %d %s"%(self.level, self.decide_history[self.level]))
        logging.info("propagate_history: %s"%", ".join([str(x)for x in self.propagate_history[self.level]]))
        one_history = self.propagate_history[self.level]
        lit_line = [self.decide_history[self.level]+[x.lit for x in one_history]]
        lower_level = set() #bind_lit
        current_level = []  #bind_lit
        done = set()        #lit
        pool = [x for x in conflict_clause.get_data()] #bind_lit

        while True:
            for blit in pool:
                assert blit.lit.get_level() <= self.level
                if blit.lit.get_level() == self.level:
                    current_level.append(blit)
                else:
                    lower_level.add(blit)

            # current_level = self._simplify_bind_literal(current_level)
            logging.info(done)
            logging.info(pool)
            logging.info([str(x)for x in current_level])
            if len(current_level) == 1:
                break

            head, tail = _popup_next_pointer(lit_line, current_level)
            done.add(head)
            pool = set([x for x in head.get_reason().get_data() if x.lit not in done])
            current_level = tail
        learnt_list = list(current_level) + list(lower_level)
        learnt_list.sort(key=lambda x:abs(x.lit.get_var())) # TODO:refactor
        backjump_level = min([x.lit.get_level()for x in learnt_list])
        learnt_clause = Clause(learnt_list, learnt=True)
        logging.info("analyze: backjump lv.%d     - %s"%(backjump_level, str(learnt_clause)))
        return backjump_level, learnt_clause

    def _decide(self, lit):
        if __debug__:
            logging.info(str(self))
        self.level += 1
        lit.assign(self.ASSIGN_DEFAULT, self.level)
        self.decide_history[self.level] = lit
        self.propagate_history[self.level] = []
        logging.info("decide %s"%str(lit))

    def _propagate(self):
        conflictiong_clause, propagatable_list = self._reload_watching_literal()
        propagatable_list_tmp = []
        while True:
            if isinstance(conflictiong_clause, Clause):
                return conflictiong_clause
            if len(propagatable_list) is 0:
                return None
            propagatable_list += propagatable_list_tmp

            blit, reason_clause = propagatable_list.pop(0)
            sign = blit.get_raw_sign()
            blit.lit.assign(sign, self.level, reason_clause)
            if self.level>0:
                self.propagate_history[self.level] += [blit]
            logging.info("propagate lit:%s c:%s"%(str(blit), str(reason_clause)))
            conflictiong_clause, propagatable_list_tmp = self._reload_watching_literal()

    def parse(self, string):
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
                self.litlist.gen_while(abs(num))
                self.litlist.get(abs(num)) #if literal is not generated,, gen lit.
            if len(s) == 0:
                return
            bll = [self.litlist.get(num).get_bindlit(num>0)for num in sorted(s,key=lambda x:abs(x))]
            return Clause(bll)
        pat = re.compile("\A[^pc]+")
        for line in string.splitlines():
            c_result = pat.search(line)
            if c_result is None:
                continue
            clause = parse_clause(c_result.group())
            if clause:
                self.add_clause(clause)
        pass


    def _reload_watching_literal(self):
        """
        reload all watching literal,
        and collect propagaltable clause

        rtype ( clause, list)
         | clause -> confling clause, or None
         | list -> tuple(BindLit,Clause), ..... propagatable_list or None
        (None, list) or (clause, None)
        """
        reason_clause = []
        for clause in self.clause_list + self.learnt_list:
            propagatable_blit = clause.update_watching_literal()
            if propagatable_blit is True:
                # sat
                pass
            elif propagatable_blit is False:
                # conflict
                return clause, None
            else:
                assert isinstance(clause, Clause)
                reason_clause += [(propagatable_blit, clause)]
        return None, reason_clause

    def _popup_literal(self):
        """
        return next decide literal.
        no literal, return None.
        rtype: Lit
        """
        for lit in self.litlist:
            if lit.is_unassigned():
                return lit
        return None

    def is_undef(self):
        """
        rype: bool
        """
        return self.status is None

    def is_sat(self):
        """
        rype: bool
        """
        return self.status is True

    def is_unsat(self):
        """
        rype: bool
        """
        return self.status is False

    def _set_default(self):
        self.status = None
        self.litlist = LitList()
        self.clause_list = []
        self.learnt_list = []
        self.decide_history = {}
        self.propagate_history = {}
        self.level = 0
        self._coflict_count = 0
        self._decide_count = 0
        self.root_level = 0

    def _str_tree(self):
        string = ""
        keys = sorted(self.propagate_history.keys())
        for key in keys:
            line = self.propagate_history[key]
            lit = self.decide_history[key]
            string += "{id:10d}: ".format(id=lit.get_var())
            string += ", ".join([str(x)for x in line])
            string += "\n"
        return string

    def __str__(self):
        string = "###############level:%d\n"%self.level
        string += "####Literals\n"+"\n".join([str(x)for x in self.litlist])
        string += "\n\n"
        string += "####Clauses\n"+"\n".join([str(x)for x in self.clause_list])
        string += "\n\n"
        string += "####Learnts\n"+"\n".join([str(x)for x in self.learnt_list])
        string += "\n\n"
        string += "####Tree\n"
        string += self._str_tree()
        return string


class Clause(object):
    """
    clause
    """
    _num = 0
    #_id: unique id
    #_data: bindlit_list
    #_learnt: if learnt from cdcl, True
    #_invalid: if you disable this clause, False ex) one literal #TODO
    #_watches: watching literal index tuple, length is 2
    def __init__(self, bindlit_list, learnt=False):
        assert isinstance(bindlit_list, list)
        assert isinstance(learnt, bool)
        self._id = self._gen_id()
        self._data = bindlit_list
        self._learnt = learnt
        self._invalid = False
        self._watching_literal = None

    def update_watching_literal(self):
        """
        return
         | True -> sat
         | False -> conflict
         | BindLit -> propagatable clause
        """
        new_watching_literal = self._next_watching_literal()
        false_lit_len = new_watching_literal.count(None)
        if false_lit_len == 1:
            # can propagate
            idx = [x for x in new_watching_literal if x is not None][0]
            bind_lit = self._data[idx]
            assert bind_lit.lit.is_unassigned() or bind_lit.get_sign() is True
            return bind_lit
        elif  false_lit_len == 0:
            self.set_watching_literal(new_watching_literal)
            return True
        else:
            assert false_lit_len == 2
            return False

    def _next_watching_literal(self):
        """
        reload wl tuple,
        if no more (unassigned or True) literal, the literal is None
        """
        assert self._watching_literal is not None, "watching literal is undefined"
        wl = self._check_watching_literal()
        for i, w_idx in enumerate(wl):
            if w_idx is None:
                # Need reload
                for idx, bind_lit in enumerate(self._data):
                    if not idx in wl:
                        if bind_lit.is_unassigned() or bind_lit.get_sign():
                            wl[i] = idx
                            break
        return tuple(wl)

    def _check_watching_literal(self):
        """
        return watching literal tuple, if the literal is False, return None.
        """
        res = [None, None]
        for i,idx in enumerate(self._watching_literal):
            try:
                lit = self._data[idx]
            except IndexError:
                # for DEBUG
                raise IndexError("list index out of range:%d"%idx)
            if lit.is_unassigned() or lit.get_sign():
                # True or unassigned, not change
                res[i] = idx
        return res

    def set_watching_literal(self, watch_tuple):
        assert isinstance(watch_tuple, tuple)
        assert len(watch_tuple) == 2
        self._watching_literal = watch_tuple

    def get_data(self):
        return self._data

    def is_learnt(self):
        return self._learnt

    @classmethod
    def _gen_id(cls):
        cls._num += 1
        return cls._num

    def __len__(self):
        return len(self._data)

    def __str__(self):
        return "{id:3d} :{watching}:{learnt}: {lits}".format(
            id=self._id,
            watching=self._watching_literal,
            lits=", ".join([str(x)for x in self._data]),
            learnt="l"if self._learnt else "-"
        )

class LitList(object):
    """
    Literal list,
    """
    # list object is 0-index, this object is 1-index
    def __init__(self):
        self._data =[]

    def get(self, lit_id):
        assert isinstance(lit_id, int)
        assert 1 <= abs(lit_id) and abs(lit_id) <= self.length(), "%d"%lit_id
        logging.debug("LitList: get - %d"%lit_id)
        return self._data[abs(lit_id)-1]

    def gen_while(self, num):
        while self.length() < num:
            self.add()

    def add(self):
        lit = Lit()
        self._data.append(lit)

    def length(self):
        return len(self._data)

    def __iter__(self):
        return iter(self._data)


class Lit(object):
    """
    Literal class
    """
    #var: (int) unique id
    #sign:
    # | None  -> Unassigned
    # | True  -> Assigned(True)
    # | False -> Assigned(False)
    #reason:
    # | None  -> decided
    # | Clause-> reason clause
    #level: (int) decision_level
    #bindlit_true: (BindLit) instance
    #bindlit_flase: (BindLit) instance
    _num = 0

    def __init__(self):
        """
        initialize Literal
        """
        self._var = self._gen_id()
        self._set_bindlit()
        self.set_default()

    def __str__(self):
        return "{var:10d}:{level}-{sign}{propagated}".format(
            var=self.get_var(),
            sign=self._sign,
            propagated="-unassigned" if self._sign is None else "-propagated"+str(self._reason._id) if self.is_propagated()else "",
            level="-"if self.is_unassigned() else self.get_level(),
        )


    def set_default(self):
        self._sign = None
        self._reason = None
        self._level = None

    def assign(self, sign, level, reason=None):
        """
        assign Literal, sign level reason.

        if propagated. "reason" argument is required
        """
        assert isinstance(sign, bool)
        assert isinstance(level, int)
        assert isinstance(reason, Clause) or reason is None
        self._sign = sign
        self._level = level
        self._reason = reason

    def get_var(self):
        return self._var

    def get_level(self):
        assert isinstance(self._level, int), 'maybe unassigned. please use "is_unassigned"'
        return self._level

    def get_reason(self):
        assert isinstance(self._reason, Clause), 'maybe decided. please use "is_propagated"'
        return self._reason

    def get_sign(self):
        assert isinstance(self._sign, bool), 'maybe unassigned. please use "is_unassigned"'
        return self._sign

    def is_unassigned(self):
        return self._level is None

    def is_propagated(self):
        return self._reason is not None

    def get_bindlit(self, sign):
        assert isinstance(sign, bool)
        if sign:
            return self.bindlit_true
        else:
            return self.bindlit_false

    def _set_bindlit(self):
        self.bindlit_true = BindLit(self, True)
        self.bindlit_false = BindLit(self, False)

    @classmethod
    def _gen_id(cls):
        cls._num += 1
        return cls._num


class BindLit(object):
    """
    For Clause, bind sign and Lit
    """
    def __init__(self, lit, sign):
        assert isinstance(lit, Lit)
        assert isinstance(sign, bool)
        self.lit = lit
        self._sign = sign

    def get_sign(self):
        """
        return BindLit sign. Not raw sign.
        ex)
            -1(BindLit)
            1(Lit) is True  -> return not(True)
            1(Lit) is False -> return not(False)
        """
        try:
            raw_sign = self.lit.get_sign()
        except AssertionError:
            raise AssertionError("use is_unassigned function")
        if self._sign:
            return self.lit.get_sign()
        else:
            return not self.lit.get_sign()

    def is_unassigned(self):
        return self.lit.is_unassigned()

    def get_raw_sign(self):
        """
        return BindLit raw sign.
        ex)
            -1(BindLit) -> raw sign is False, return False
        """
        return self._sign

    def __str__(self):
        if self._sign:
            return " %2d"%self.lit.get_var()
        else:
            return "-%2d"%self.lit.get_var()






if __name__ == '__main__':
    if len(sys.argv) == 2:
        string = open(sys.argv[1]).read()
        solver = Solver()
        solver.parse(string)

        print(solver)

        solver.solve()
        print(solver.status)
        print(solver)
        solver.print_result()