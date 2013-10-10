import logging
import sys
import re

ASSIGN_DEFAULT = True

if __debug__:
    #logging.basicConfig(level=logging.INFO, filename="log")
    logging.basicConfig(level=logging.DEBUG)

class NoUnsignedException(BaseException):
    pass

class ConflictException(BaseException):
    pass

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
    num = 0

    def __init__(self):
        """
        initialize a Literal
        """
        self._var = self._inc_var()
        self._sign = None #(None|True|False)
        self._reason = None #pointer to reason clause if propagated
        self._level = None #if decision level is None, this is unassigned

    def __str__(self, fmt="{var:10d}:{level}-{sign}{propagated}"):
        """
        You can specify format string as "fmt" argument.
        """
        return fmt.format(
            var=self.get_var(),
            sign=self._sign,
            propagated="-unassigned" if self._sign is None else "-propagated"+str(self._reason._id) if self.get_reason()else "",
            level=self.get_level()
        )

    def set_default(self):
        """
        clear Literal state.

        Called when Literal withdraw.
        """
        self._sign = None #(None|True|False)
        self._reason = None #pointer to reason clause if propagated
        self._level = None #if decision level is None, this is unassigned

    def assign(self, sign, level, reason=None):
        """
        assign Literal, sign level reason.

        if propagated, "reason" argument is require.
        """
        self._sign = sign
        self._level = level
        self._reason = reason

    def reverse(self):
        """
        reverse Literal's sign
        """
        self._sign = not self._sign

    def get_var(self):
        return self._var

    def get_level(self):
        return self._level

    def get_reason(self):
        return self._reason

    def get_sign(self):
        return self._sign

    def is_unassigned(self):
        return self._level is None

    @classmethod
    def _inc_var(cls):
        cls.num += 1
        return cls.num


class BindLit(object):
    """
    Bind Literal and sign, for Clause's Literal.

    This class has sign and literal,
    """

    def __init__(self, lit, sign):
        self.lit = lit
        self._sign = sign

    def __str__(self):
        if self._sign:
            return " %2d"%self.lit.get_var()
        else:
            return "-%2d"%self.lit.get_var()

    def get_sign(self):
        if self.lit.get_sign() is None:
            return None
        if self._sign:
            return self.lit.get_sign()
        else:
            return not self.lit.get_sign()

    def get_raw_sign(self):
        return self._sign


class LitList(object):
    """
    Literal's list, data struct 

    it similar to stack or queue.
    """

    def __init__(self):
        self._lit_list = []

    def __str__(self):
        return "\n".join([str(x)for x in self._lit_list])

    def __iter__(self):
        return iter(self._lit_list)

    def get(self, key):
        """
        get Literal

        key is list's index(1-index).
        """
        logging.debug("LL-getitem:{k}".format(k=key))
        assert isinstance(key, int), "LL-keyerror"
        lit = self._lit_list[abs(key)-1]
        return lit

    def add(self, lit):
        self._lit_list.append(lit)

    def length(self):
        return len(self._lit_list)


class Clause(object):
    """
    clause
    """
    num = 0
    #_id: unique id
    #_data: bindlitlist(list)
    #_learnt: if learnt from cdcl, True
    #_invalid: if you diable this clause, set True #TODO
    #_watches: watching literal index tuple

    def __init__(self, bind_lit_list, learnt=False):
        self._id = self._gen_id() # 1 index
        self._data = bind_lit_list
        self._learnt = learnt
        self._invalid = False #true when one literal etc...
        self._watches = None #(idx1, idx2)

    def __str__(self):
        return "{id:3d} :{watching}:{learnt}: {lits}".format(
            id=self._id,
            watching=self._watches,
            lits=", ".join([str(x)for x in self._data]),
            learnt="l"if self._learnt else "-"
        )

    def _check_watches(self):
        assert self._watches is not None, "watches is not set"
        res = [None, None]
        #for i in range(2):
        #    w_idx = self._watches[i]

        #    if self._data[w_idx].get_sign() is False: # when false
        #        for idx, bind_lit in enumerate(self._data):
        #            if bind_lit.get_sign() is not False: # find next watches
        #                if not idx in res: # not already used
        #                    res[i] = idx
        #                    break
        #        # if no more unassigned lit, it remains as None.
        #    else:
        #        # no change
        #        res[i] = w_idx
        for i,w_idx in enumerate(self._watches):
            try:#DEBUF ATODE KESE#DEBUF aATODE KESE#DEBUF aATODE KESE
                self._data[w_idx]
            except:
                logging.info(w_idx)
                logging.info(str(self))
            if self._data[w_idx].get_sign() is not False:
                #no change
                res[i] = w_idx
        for i,w_idx in enumerate(self._watches):
            for idx, bind_lit in enumerate(self._data):
                if bind_lit.get_sign() is not False:
                    if not idx in res:
                        res[i] = idx
                        break
        return tuple(res)

    def set_watching_literal(self, watches):
        """
        set watching literal

        watches is tuple(idx1, idx2)
        int
        """
        self._watches = watches

    def update_watching_literal(self):
        """
        return
        | 1 -> sat
        |-1 -> unsat
        |clause -> can propagate
        """
        new_watches = self._check_watches()
        false_lit_num = new_watches.count(None)
        if false_lit_num == 0:
            self.set_watching_literal(new_watches)
            return 1
        elif false_lit_num == 1:
            # can propagate
            idx = [x for x in new_watches if x is not None]
            assert len(idx) == 1
            c = self._data[idx[0]]
            if c.get_sign():
                # if the lit is true, it is already propagated
                return 1
            else:
                return c
        else:
            return -1

    def length(self):
        """
        return clause's length
        """
        return len(self._data)

    def simplify(self):
        """
        if duplicate literal, return True
        """
        #TODO: rename to is_simplify
        if len(set([x.lit for x in self._data])) < len(self._data):
            return True
        return False

    def get_data(self):
        return self._data

    def is_learnt(self):
        return self._learnt

    def is_invalid(self):
        return self._invalid

    def is_sat(self):
        """
        if exist unsigned literal, return None
        if sat, return True
        if unsat, return False
        """
        for bind_lit in self._data:
            if bind_lit.lit.is_unassigned():
                return None
            else:
                if bind_lit.get_sign():
                    return True
        return False

    @classmethod
    def _gen_id(cls):
        cls.num +=1
        return cls.num


class Solver(object):
    #status
    # | True  -> Satisfied
    # | None  -> Unassined
    # | False -> Unsatisfied
    #
    #litlist          -> LitList
    #clause_list      -> list
    #learnt_list      -> list
    #propagate_histry -> list
    #level            -> int

    def __init__(self):
        self._set_defulat()

    def _set_defulat(self):
        self.status = None
        self.litlist = LitList()
        self.clause_list = []
        self.learnt_list = []
        self.decide_histry = {}
        self.propagate_histry = {}
        self.level = 0

        self.conflict_count = 0
        self.root_level = 0

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

    def add_clause(self, clause):
        assert isinstance(clause, Clause)
        assert (clause.length() >= 1), str(clause)
        data = clause.get_data()
        if len(data) == 1:
            bind_lit = data[0]
            sign = bind_lit.get_raw_sign()
            bind_lit.lit.assign(sign, self.root_level)
            return
        clause.set_watching_literal((0,1))
        if clause.is_learnt():
            self.learnt_list.append(clause)
        else:
            self.clause_list.append(clause)

    def solve(self):
        logging.debug("solve")
        logging.info(str(self))
        while self.is_undef():
            self._search()
        self.print_result

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

    def _search(self):
        if not self.is_undef():
            return
        while True:
            conflict_clause = self.propagate()
            if conflict_clause is not None:
                # CONFLICT
                
                #self.conflict_count += 1
                if self.level == self.root_level:
                    # contradiction
                    self.status = False
                    return
                backjump_level, learnt_clause = self.analyze(conflict_clause)
                self.add_clause(learnt_clause)
                self.cancel_until(backjump_level)
                self.level = backjump_level-1
                logging.info("search backjump %d"%backjump_level)
                pass
            else:
                # NO CONFLICT
                
                #TODO:restart here
                #self._decide_count += 1
                decide_literal = self.popup_literal()
                if decide_literal is None:
                    # SATISFIED
                    self.status = True
                    return
                else:
                    self.decide(decide_literal)
    
    def analyze(self, conflict_clause):
        def _popup_next_pointer(base_lit_list, blit_list):
            """
            function for CDCL. searching first UIP
            return (lit, others)
             | lit -> lit
             | others -> bindlit list
            """
            data = [x.lit for x in blit_list]
            for lit in reversed(base_lit_list):
                if lit in data:
                    others = [x for x in blit_list if lit is not x.lit]
                    return lit, others

        logging.info("analyze %s"%str(conflict_clause))
        logging.info("level %d %s"%(self.level,self.decide_histry[self.level]))
        logging.info("propagate_histry:%s"%", ".join([str(x)for x in self.propagate_histry[self.level]]))
        
        onehistry = self.propagate_histry[self.level]
        lit_line = [self.decide_histry[self.level]]+[x.lit for x in onehistry]
        lower_level = set() #bindlit
        current_level = [] #bindlit
        done = set() #lit
        pool = [x for x in conflict_clause.get_data()]

        while True:
            for blit in pool:
                assert blit.lit.get_level() <= self.level
                if blit.lit.get_level() == self.level:
                    current_level.append(blit)
                else:
                    lower_level.add(blit)
            current_level = self._simplify_bind_literal(current_level)

            logging.info(done)
            logging.info(pool)
            logging.info([str(x)for x in current_level])
            if len(current_level) == 1:
                break

            head, tail = _popup_next_pointer(lit_line, current_level)
            
            done.add(head)
            pool = set([x for x in head.get_reason().get_data()if x.lit not in done])
            current_level = tail

        learnt_list = list(current_level) + list(lower_level)
        learnt_list.sort(key=lambda x:abs(x.lit.get_var())) # TODO:refactor
        backjump_level = min([x.lit.get_level()for x in learnt_list])
        learnt_clause = Clause(learnt_list, learnt=True)
        logging.info("analyze: backjump%d    - %s"%(backjump_level, str(learnt_clause)))
        return backjump_level, learnt_clause

    def _simplify_bind_literal(self, blit_list):
        tmp = {}
        for blit in blit_list:
            tmp[str(blit)] = blit
        return tmp.values()

    def popup_literal(self):
        for lit in self.litlist:
            if lit.is_unassigned():
                return lit
        return None

    def cancel_until(self, level):
        assert type(level) is int
        for lit in self.litlist:
            if lit.get_level()>=level:
                if isinstance(lit, Lit):
                    lit.set_default()
                else:
                    lit.lit.set_default()
        if level>0:
            self.decide_histry[level].set_default()
        for key in self.propagate_histry.keys():
            if key >= level:
                del self.propagate_histry[key]
        if level>0:
            del self.decide_histry[level]


    def _gen_lit(self,num):
        while(self.litlist.length() < num):
            lit = Lit()
            self.litlist.add(lit)

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
                self._gen_lit(abs(num)) #if literal is not generated,, gen lit.
            if len(s) == 0:
                return
            bll = [BindLit(self.litlist.get(num),num>0)for num in sorted(s,key=lambda x:abs(x))]
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

    def _str_tree(self):
        string = ""
        keys = sorted(self.propagate_histry.keys())
        for key in keys:
            line = self.propagate_histry[key]
            lit = self.decide_histry[key]
            string += "{id:10d}: ".format(id=lit.get_var())
            string += ", ".join([str(x)for x in line])
            string += "\n"
        return string

    def decide(self, lit, sign=ASSIGN_DEFAULT):
        if __debug__:
            logging.info(str(self))
        self.level += 1
        lit.assign(sign, self.level)
        self.decide_histry[self.level] = lit
        self.propagate_histry[self.level] = []
        logging.info("decide {lit}".format(lit=str(lit),sign=lit.get_sign()))

    def propagate(self):
        wl = self.reload_watches()
        if wl.unsat:
            return None
        level = self.level
        res = self._propagate(wl, level)
        return res

    def _propagate(self, wl, level):
        """
        if conflict return conflicting clause
        """
        stack = wl.lit_list
        for n in self.litlist:
            if wl.unsat:
                return wl.clause
            if wl.lit_list == []:
                break
            bind_lit, reason = stack.pop()
            sign = bind_lit.get_raw_sign()
            logging.info("propagate lit:{lit} c:{c}".format(lit=str(bind_lit),c=str(reason)))
            bind_lit.lit.assign(sign, level, reason)
            if level > 0:
                self.propagate_histry[level] += [bind_lit]
            wl = self.reload_watches()
            stack = [x for x in wl.lit_list if x not in stack]+stack
            pass
    def reload_watches(self):
        """
        return
        status
             1 -> all sat or unassigned
             0 -> can propagate, data=propagatable literal list
            -1 -> unsat, data=conflicting clause
        """
        class res:pass
        res.status = None
        res.propagate = False
        res.unsat = False
        res.lit_list = []
        res.clause = None

        l = []
        for c in self.clause_list+self.learnt_list:
            tmp = c.update_watching_literal()

            if isinstance(tmp, BindLit):
                #propagate
                l.append((tmp,c))
            elif tmp == 1:
                #SAT
                pass
            elif (res.status is None) and tmp == -1:
                #unsat
                res.status = -1
                res.unsat = True
                res.clause = c
        if res.status is None:
            if l == []:
                res.status = 1
            else:
                res.status = 0
                res.propagate = True
                res.lit_list = l
        return  res
    
    def is_sat(self):
        return self.status is True

    def is_undef(self):
        return self.status is None

    def is_unsat(self):
        return self.status is False

if __name__  == "__main__":
    if len(sys.argv) == 2:
        string = open(sys.argv[1]).read()
        solver = Solver()
        solver.parse(string)

        print(solver)

        solver.solve()
        print(solver.status)
        print(solver)
        solver.print_result()
