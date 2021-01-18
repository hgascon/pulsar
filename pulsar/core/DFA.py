# python-automata, the Python DFA library
# License: New BSD License
# Author: Andrew Badr
# Version: June 21, 2007
# Contact: andrewbadr@gmail.com
# Code contributions are welcome.

def delta(state, obs):
    oldObs = state.split("|")
    if len(oldObs) > 1:
        newObs = oldObs[1:]
        newObs.append(obs)
    else:
        newObs = [obs]
    return "|".join(newObs)

# m = lens.MarkovModel("data/robot.markovModel")
# d = DFA.prismaModel2DFA(m.getSimplifiedModel())
# equi = d.minimize()
# [['BASE.UAS|END'],
# ['CARRY.UAC|BASE.UAS'],
# ['BASE.UAS|GO.UAC', 'FREE.UAS|GO.UAC', 'START|GO.UAC', 'WALL.UAS|GO.UAC'],
# ['GO.UAC|WALL.UAS', 'GO.UAC|BASE.UAS', 'GO.UAC|FREE.UAS', 'START|START'],
# ['BROKEN_END'],
# ['FREE.UAS|CARRY.UAC', 'OBJECT.UAS|CARRY.UAC'],
# ['WALL.UAS|CARRY.UAC'],
# ['CARRY.UAC|FREE.UAS', 'GO.UAC|OBJECT.UAS'],
# ['CARRY.UAC|WALL.UAS']]
# m.exportMarkovMartrix("data/robot.markovMatrix")
# in R:
# m = read.table("data/robot.markovMatrix", sep="\t", header=TRUE)
# m[c('GO.UAC|WALL.UAS', 'GO.UAC|BASE.UAS', 'GO.UAC|FREE.UAS', 'START|START'), ]
def prismaModel2DFA(model):
    # gather the states
    allStates = model.copy()
    [allStates.update(val) for val in model.values()]
    # now the keys of the dictionary are the states
    allStates = list(allStates.keys())
    allStates.append("BROKEN_END")
    # split the states for the according alphabet
    alphabet = set([ss for state in allStates for ss in state.split("|")])
    order = allStates[0].count("|") + 1
    start = "|".join(["START"] * order)
    accepts = [state for state in allStates if state.endswith("|END")]
    def modelDelta(state, obs):
        newState = delta(state, obs)
        if newState in model.get(state, {}):
            return newState
        else:
            return "BROKEN_END"
    dfa = DFA(allStates, alphabet, modelDelta, start, accepts)
    return(dfa)

# import pygraphviz; G = pygraphviz.AGraph(DFA.DFA2prismaModel(dfar), directed=True); G.draw("data/robotMinimized.pdf", prog="dot")
def DFA2prismaModel(dfa):
    model = {}
    for state in dfa.states:
        for trans in dfa.alphabet:
            if trans == "BROKEN_END":
                continue
            nextState = dfa.delta(state, trans)
            if nextState == "BROKEN_END":
                continue
            model.setdefault(state, {})[nextState] = True
    return model

class DFA:
    """This class represents a deterministic finite automon."""
    def __init__(self, states, alphabet, delta, start, accepts):
        """The inputs to the class are as follows:
         -states: a lists containing the states of the DFA
         -alphabet: a list containing the symbols in the DFA's alphabet
         -delta: a complete function from [states]x[alphabets]->[states].
         -start: the state at which the DFA begins operation.
         -accepts: a list containing the "accepting" or "final" states of the DFA

        Making delta a function rather than a transition table makes it much easier to define certain DFAs. 
        And if you want to use transition tables, you can just do this:
         delta = lambda q,c: transition_table[q][c]
        One caveat is that the function should not depend on the value of 'states' or 'accepts', since
        these may be modified during minimization.

        Finally, the names of states and inputs should be hashable. This generally means strings, numbers,
        or tuples of hashables.
        """
        self.states = states
        self.start = start
        self.delta = delta
        self.accepts = accepts
        self.alphabet = alphabet
        self.current_state = start
#
# Administrative functions:
#
    def pretty_print(self):
        """Displays all information about the DFA in an easy-to-read way. Not
        actually that easy to read if it has too many states.
        """
        print("")
        print("This DFA has %s states" % len(self.states))
        print("States:", self.states)
        print("Alphabet:", self.alphabet)
        print("Starting state:", self.start)
        print("Accepting states:", self.accepts)
        print("Transition function:")
        print("\t","\t".join(map(str,self.states)))
        for c in self.alphabet:
            results = [self.delta(x, c) for x in self.states]
            print(c, "\t", "\t".join(map(str, results)))
        print("Current state:", self.current_state)
        print("Currently accepting:", self.status())
        print("")
    def validate(self):
        """Checks that: 
        (1) The accepting-state set is a subset of the state set.
        (2) The start-state is a member of the state set.
        (3) The current-state is a member of the state set.
        (4) Every transition returns a member of the state set.

        Obviously, this function will not work on infinite DFAs
        """
        assert set(self.accepts).issubset(set(self.states))
        assert self.start in self.states
        assert self.current_state in self.states
        for state in self.states:
            for char in self.alphabet:
                assert self.delta(state, char) in self.states
    def copy(self):
        """Returns a copy of the DFA. No data is shared with the original."""
        from copy import copy
        return DFA(copy(self.states), copy(self.alphabet), self.delta, self.start, copy(self.accepts))

#
# Simulating execution:
#
    def input(self, char):
        """Updates the DFA's current state based on a single character of input."""
        self.current_state = self.delta(self.current_state, char)
    def input_sequence(self, char_sequence):
        """Updates the DFA's current state based on an iterable of inputs."""
        for char in char_sequence:
            self.input(char)
    def status(self):
        """Indicates whether the DFA's current state is accepting."""
        return (self.current_state in self.accepts)
    def reset(self):
        """Returns the DFA to the starting state."""
        self.current_state = self.start
    def recognizes(self, char_sequence):
        """Indicates whether the DFA accepts a given string."""
        state_save = self.current_state
        self.reset()
        self.input_sequence(char_sequence)
        valid = self.status()
        self.current_state = state_save
        return valid
#
# Minimization methods and their helper functions
#
    def state_hash(self, value):
        """Creates a hash with one key for every state in the DFA, and
        all values initialized to the 'value' passed.
        """
        hash = {}
        for state in self.states:
            if value == {}:
                hash[state] = {}
            elif value == []:
                hash[state] = []
            else:
                hash[state] = value
        return hash
    def state_subset_hash(self, subset):
        """Creates a hash with one key for every state in the DFA, with
        the value True for states in 'subset' and False for all others.
        """
        hash = self.state_hash(False)
        for q in subset:
            hash[q] = True
        return hash
    def state_merge(self, q1, q2):
        """Merges q1 into q2. All transitions to q1 are moved to q2.
        If q1 was the start or current state, those are also moved to q2.
        """
        self.states.remove(q1)
        if q1 in self.accepts:
            self.accepts.remove(q1)
        if self.current_state == q1:
            self.current_state = q2
        if self.start == q1:
            self.start = q2
        transitions = {}
        for state in self.states: #without q1
            transitions[state] = {}
            for char in self.alphabet:
                next = self.delta(state, char)
                if next == q1:
                    next = q2
                transitions[state][char] = next
        self.delta = (lambda s, c: transitions[s][c])
    def reachable_from(self, q0, inclusive=True):
        """Returns the set of states reachable from given state q0. The optional
        parameter "inclusive" indicates that q0 should always be included.
        """
        reached = self.state_hash(False)
        if inclusive:
            reached[q0] = True
        to_process = [q0]
        while len(to_process):
            q = to_process.pop()
            for c in self.alphabet:
                next = self.delta(q, c)
                if reached[next] == False:
                    reached[next] = True
                    to_process.append(next)
        return [q for q in self.states if reached[q]]
    def reachable(self):
        """Returns the reachable subset of the DFA's states."""
        return self.reachable_from(self.start)
    def delete_unreachable(self):
        """Deletes all the unreachable states."""
        reachable = self.reachable()
        self.states = reachable
        new_accepts = []
        for q in self.accepts:
            if q in self.states:
                new_accepts.append(q)
        self.accepts = new_accepts
    def mh_classes(self):
        """Returns a partition of self.states into Myhill-Nerode equivalence classes."""
        changed = True
        classes = []
        if self.accepts != []:
            classes.append(self.accepts)
        nonaccepts = [x for x in self.states if x not in self.accepts]
        if nonaccepts != []:
            classes.append(nonaccepts)
        while changed:
            changed = False
            for cl in classes:
                local_change = False
                for alpha in self.alphabet:
                    next_class = None
                    new_class = []
                    for state in cl:
                        next = self.delta(state, alpha)
                        if next_class == None:
                            for c in classes:
                                if next in c:
                                    next_class = c
                        elif next not in next_class:
                            new_class.append(state)
                            changed = True
                            local_change = True
                    if local_change == True:
                        old_class = []
                        for c in cl:
                            if c not in new_class:
                                old_class.append(c)
                        classes.remove(cl)
                        classes.append(old_class)
                        classes.append(new_class)
                        break
        return classes
    def collapse(self, partition):
        """Given a partition of the DFA's states into equivalence classes,
        collapses every equivalence class into a single "representative" state.
        Returns the hash mapping each old state to its new representative.
        """
        new_states = []
        new_start = None
        new_delta = None
        new_accepts = []
        #alphabet stays the same
        new_current_state = None
        state_map = {}
        #build new_states, new_start, new_current_state:
        for state_class in partition:
            representative = state_class[0]
            new_states.append(representative)
            for state in state_class:
                state_map[state] = representative
                if state == self.start:
                    new_start = representative
                if state == self.current_state:
                    new_current_state = representative
        #build new_accepts:
        for acc in self.accepts:
            if acc in new_states:
                new_accepts.append(acc)
        #build new_delta:
        transitions = {}
        for state in new_states:
            transitions[state] = {}
            for alpha in self.alphabet:
                transitions[state][alpha] = state_map[self.delta(state, alpha)]
        new_delta = (lambda s, a: transitions[s][a])
        self.states = new_states
        self.start = new_start
        self.delta = new_delta
        self.accepts = new_accepts
        self.current_state = new_current_state
        return state_map
    def minimize(self):
        """Classical DFA minimization, using the simple O(n^2) algorithm.
        Side effect: can mix up the internal ordering of states.
        """
        #Step 1: Delete unreachable states
        self.delete_unreachable()
        #Step 2: Partition the states into equivalence classes        
        classes = self.mh_classes()
        #Step 3: Construct the new DFA
        self.collapse(classes)
        return classes
        
    def pluck_leaves(self):
        """Only for minimized automata. Returns a topologically ordered list of
        all the states that induce a finite language. Runs in linear time.
        """
        #Step 1: Build the states' profiles
        loops    = self.state_hash(0)
        inbound  = self.state_hash([])
        outbound = self.state_hash([])
        accepts  = self.state_subset_hash(self.accepts)
        for state in self.states:
            for c in self.alphabet:
                next = self.delta(state, c)
                inbound[next].append(state)
                outbound[state].append(next)
                if state == next:
                    loops[state] += 1
        #Step 2: Add sink state to to_pluck
        to_pluck = []
        for state in self.states:
            if len(outbound[state]) == loops[state]:
                if not accepts[state]:
                    to_pluck.append(state)
        #Step 3: Pluck!
        plucked = []
        while len(to_pluck):
            state = to_pluck.pop()
            plucked.append(state)
            for incoming in inbound[state]:
                outbound[incoming].remove(state)
                if (len(outbound[incoming]) == 0) and (incoming != state):
                    to_pluck.append(incoming)
        plucked.reverse()
        return plucked
    def is_finite(self):
        """Indicates whether the DFA's language is a finite set."""
        D2 = self.copy()
        D2.minimize()
        plucked = D2.pluck_leaves()
        return (D2.start in plucked)
    def levels(self):
        """Returns a dictionary mapping each state to its distance from the starting state."""
        levels = {}
        seen = [self.start]
        levels[self.start] = 0
        level_number = 0
        level_states = [self.start]
        while len(level_states):
            next_level_states = []
            next_level_number = level_number + 1
            for q in level_states:
                for c in self.alphabet:
                    next = self.delta(q, c)
                    if next not in seen:
                        seen.append(next)
                        levels[next] = next_level_number
                        next_level_states.append(next)
            level_states = next_level_states
            level_number = next_level_number
        return levels
    def longest_word_length(self):
        """Given a DFA recognizing a finite language, returns the length of the
        longest word in that language, or None if the language is empty.
        """
        assert(self.is_finite())
        def long_path(q,length, longest):
            if q in self.accepts:
                if length > longest:
                    longest = length
            for char in self.alphabet:
                next = self.delta(q, char)
                if next != q:
                     candidate = long_path(next, length+1, longest)
                     if candidate > longest:
                         longest = candidate
            return longest
        return long_path(self.start, 0, None)
    def DFCA_minimize(self, l=None):
        """DFCA minimization'
        Input: 'self' is a DFA accepting a finite language
        Result: 'self' is DFCA-minimized, and the returned value is the length of the longest
                word accepted by the original DFA

        See 'Minimal cover-automata for finite languages' for context on DFCAs, and
        'An O(n^2) Algorithm for Constructing Minimal Cover Automata for Finite Languages'
        for the source of this algorithm (Campeanu, Paun, Santean, and Yu). We follow their
        algorithm exactly, except that 'l' is optionally calculated for you, and the state-
        ordering is automatically created.
        
        There exists a faster, O(n*logn)-time algorithm due to Korner, from CIAA 2002.
        """
        assert(self.is_finite())
        self.minimize()
        ###Step 0: Numbering the states and computing "l"
        n = len(self.states) - 1
        state_order = self.pluck_leaves()
        if l==None:
            l = self.longest_word_length()
        #We're giving each state a numerical name so that the  algorithm can 
        # run on an "ordered" DFA -- see the paper for why. These functions
        # allow us to copiously convert between names.
        def nn(q): # "numerical name"
            return state_order.index(q)
        def rn(n): # "real name"
            return state_order[n]

        ###Step 1: Computing the gap function
        # 1.1
        level = self.levels() #holds real names
        gap = {}  #holds numerical names
        # 1.2 
        for i in range(n):
            gap[(i, n)] = l
        if level[rn(n)] <= l:
            for q in self.accepts:
                gap[(nn(q), n)] = 0
        # 1.3
        for i in range(n-1):
            for j in range(i+1, n):
                if (rn(i) in self.accepts)^(rn(j) in self.accepts):
                    gap[(i,j)] = 0
                else:
                    gap[(i,j)] = l
        # 1.4
        def level_range(i, j):
            return l - max(level[rn(i)], level[rn(j)])
        for i in range(n-2, -1, -1):
            for j in range(n, i, -1):
                for char in self.alphabet:
                    i2 = nn(self.delta(rn(i), char))
                    j2 = nn(self.delta(rn(j), char))
                    if i2 != j2:
                        if i2 < j2:
                            g = gap[(i2, j2)]
                        else:
                            g = gap[(j2, i2)]
                        if g+1 <= level_range(i, j):
                            gap[(i,j)] = min(gap[(i,j)], g+1)
        ###Step 2: Merging states
        # 2.1
        P = {}
        for i in range(n+1):
            P[i] = False
        # 2.2
        for i in range(n):
            if P[i] == False:
                for j in range(i+1, n+1):
                    if (P[j] == False) and (gap[(i,j)] == l):
                        self.state_merge(rn(j), rn(i))
                        P[j] = True
        return l


#
# Boolean set operations on languages -- end of the DFA class
#
def cross_product(D1, D2, accept_method):
    """A generalized cross-product constructor over two DFAs. 
    The third argument is a binary boolean function f; a state (q1, q2) in the final
    DFA accepts if f(A[q1],A[q2]), where A indicates the acceptance-value of the state.
    """
    from copy import copy
    assert(D1.alphabet == D2.alphabet)
    states = []
    for s1 in D1.states:
        for s2 in D2.states:
            states.append((s1,s2))
    start = (D1.start, D2.start)
    def delta(state_pair, char):
        next_D1 = D1.delta(state_pair[0], char)
        next_D2 = D2.delta(state_pair[1], char)
        return (next_D1, next_D2)
    alphabet = copy(D1.alphabet)
    accepts = []
    D1_accepts = D1.state_subset_hash(D1.accepts) #we like to keep things O(n^2) around here...
    D2_accepts = D2.state_subset_hash(D2.accepts)
    for (s1, s2) in states:
        a1 = D1_accepts[s1]
        a2 = D2_accepts[s2]
        if accept_method(a1, a2):
            accepts.append((s1, s2))
    return DFA(states=states, start=start, delta=delta, accepts=accepts, alphabet=alphabet)
def intersection(D1, D2):
    """Constructs an unminimized DFA recognizing the intersection of the languages of two given DFAs."""
    f = bool.__and__
    return cross_product(D1, D2, f)

def union(D1, D2):
    """Constructs an unminimized DFA recognizing the union of the languages of two given DFAs."""
    f = bool.__or__
    return cross_product(D1, D2, f)

def symmetric_difference(D1, D2):
    """Constructs an unminimized DFA recognizing the symmetric difference of the languages of two given DFAs."""
    f = bool.__xor__
    return cross_product(D1, D2, f)

def inverse(D):
    """Constructs an unminimized DFA recognizing the inverse of the language of a given DFA."""
    new_accepts = []
    for state in D.states:
        if state not in D.accepts:
            new_accepts.append(state)
    return DFA(states=D.states, start=D.start, delta=D.delta, accepts=new_accepts, alphabet=D.alphabet)
# 
# Constructing new DFAs
# 
def from_word_list(language, alphabet):
    """Constructs an unminimized DFA accepting the given finite language."""
    from copy import copy
    accepts = language
    start = ''
    sink = 'sink'
    states = [start, sink]
    for word in language:
        for i in range(len(word)):
            prefix = word[:i+1]
            if prefix not in states:
                states.append(prefix)
    fwl = copy(states)
    def delta(q, c):
        next = q+c
        if next in fwl:
            return next
        else:
            return sink
    return DFA(states=states, alphabet=alphabet, delta=delta, start=start, accepts=accepts)
def modular_zero(n, base=2):
    """Returns a DFA that accepts all binary numbers equal to 0 mod n. Use the optional
    parameter "base" if you want something other than binary. The empty string is also 
    included in the DFA's language.
    """
    states = list(range(n))
    alphabet = list(map(str, list(range(base))))
    delta = lambda q, c: ((q*base+int(c)) % n)
    start = 0
    accepts = [0]
    return DFA(states=states, alphabet=alphabet, delta=delta, start=start, accepts=accepts)
def random(states_size, alphabet_size, acceptance=0.5):
    """Constructs a random DFA with "states_size" states and "alphabet_size" inputs. Each 
    transition destination is chosen uniformly at random, so the resultant DFA may have 
    unreachable states. The optional "acceptance" parameter indicates what fraction of 
    the states should be accepting.
    """
    import random
    states = list(range(states_size))
    start = 0
    alphabet = list(range(alphabet_size))
    accepts = random.sample(states, int(acceptance*states_size))
    tt = {}
    for q in states:
        tt[q] = {}
        for c in alphabet:
            tt[q][c] = random.choice(states)
    delta = lambda q, c: tt[q][c]
    return DFA(states, alphabet, delta, start, accepts)
