from abc import ABCMeta, abstractmethod
import sys
from collections import deque
import json
import graphviz


class FA(metaclass=ABCMeta):
    lambdaSymbol = '@'
    trapState = -1

    def __init__(self, states, alphabet, transitions, initial, final):
        self.states = states
        self.alphabet = alphabet
        self.transitions = transitions
        self.initial = initial
        self.final = final

    @abstractmethod
    def accepts(self, input):
        pass

    @abstractmethod
    def toJson(self):
        pass

    @abstractmethod
    def visualize(self):
        pass


class DFA(FA):
    def __init__(self, states, alphabet, transitions, initial, final):
        super().__init__(states, alphabet, transitions, initial, final)

    def accepts(self, input):
        currentState = self.initial
        for i in range(0, len(input)):
            try:
                currentState = self.transitions[currentState][input[i]]
            except KeyError:
                return False
        if currentState in self.final:
            return True
        else:
            return False

    def toJson(self):
        toConvert = {}
        toConvert["states"] = self.states
        toConvert["alphabet"] = self.alphabet
        toConvert["transitions"] = self.transitions
        toConvert["initial"] = self.initial
        toConvert["final"] = self.final
        return json.dumps(toConvert)

    def visualize(self):
        graph = graphviz.Digraph(format="png")
        graph.node("fake", style="invisible")
        for state in self.states:
            if state == self.initial:
                if state in self.final:
                    graph.node(str(state), root="true", shape="doublecircle")
                else:
                    graph.node(str(state), root="true")
            elif state in self.final:
                graph.node(str(state), shape="doublecircle")
            else:
                graph.node(str(state))

        graph.edge("fake", str(self.initial), style="bold")
        for start in self.states:
            for w in (self.alphabet+list(self.lambdaSymbol)):
                if start in self.transitions and w in self.transitions[start]:
                    graph.edge(str(start), str(self.transitions[start][w]), label=str(w))

        return graph

    # Hopcroft's Algorithm
    def minimize(self):
        p = set()
        w = set()
        nonFinal = list(filter(lambda x: x not in self.final, self.states))
        p.add(frozenset(nonFinal))
        p.add(frozenset(self.final))

        w.add(frozenset(nonFinal))
        w.add(frozenset(self.final))

        while(len(w) > 0):
            a = w.pop()
            for c in self.alphabet:
                p_copy = p.copy()
                for y in p:
                    yMinusX = set()
                    yinterX = set()
                    for state in y:
                        if self.transitions[state][c] in a:
                            yinterX.add(state)
                        else:
                            yMinusX.add(state)
                    if len(yinterX) > 0 and len(yMinusX) > 0:
                        p_copy.remove(y)
                        p_copy.add(frozenset(yinterX))
                        p_copy.add(frozenset(yMinusX))
                        if y in w:
                            w.remove(y)
                            w.add(frozenset(yinterX))
                            w.add(frozenset(yMinusX))
                        else:
                            if len(yinterX) <= len(yMinusX):
                                w.add(frozenset(yinterX))
                            else:
                                w.add(frozenset(yMinusX))
                p = p_copy

        stateCounter = 1
        dfa_transitions = {}
        dfa_dict = {}
        dfa_finalStates = []
        unminimizedFinalStatesSet = set(self.final)
        for newState in p:
            if self.initial in newState:
                dfa_dict[newState] = 0
                if not newState.isdisjoint(unminimizedFinalStatesSet):
                    dfa_finalStates.append(0)
                continue
            dfa_dict[newState] = stateCounter
            if not newState.isdisjoint(unminimizedFinalStatesSet):
                dfa_finalStates.append(stateCounter)
            stateCounter += 1

        for newState in p:
            for w in self.alphabet:
                state = next(iter(newState))
                goesTo = self.transitions[state][w]
                for ss in p:
                    if goesTo in ss:
                        dfa_transitions.setdefault(dfa_dict[newState], {})[w] = dfa_dict[ss]

        return DFA(list(range(0, len(p))), self.alphabet, dfa_transitions, self.initial, dfa_finalStates)


class NFA(FA):
    def __init__(self, states, alphabet, transitions, initial, final):
        super().__init__(states, alphabet, transitions, initial, final)
        self.correspondingDFA = None

    def accepts(self, input):
        if self.correspondingDFA is None:
            self.correspondingDFA = self.toDFA()
        return self.correspondingDFA.accepts(input)

    def toJson(self):
        toConvert = {}
        toConvert["states"] = self.states
        toConvert["alphabet"] = self.alphabet
        toConvert["transitions"] = self.transitions
        toConvert["initial"] = self.initial
        toConvert["final"] = self.final
        return json.dumps(toConvert)

    def visualize(self):
        graph = graphviz.Digraph(format="png")
        graph.node("fake", style="invisible")
        for state in self.states:
            if state == self.initial:
                if state in self.final:
                    graph.node(str(state), root="true", shape="doublecircle")
                else:
                    graph.node(str(state), root="true")
            elif state in self.final:
                graph.node(str(state), shape="doublecircle")
            else:
                graph.node(str(state))

        graph.edge("fake", str(self.initial), style="bold")

        for start in self.states:
            for w in (self.alphabet+list(self.lambdaSymbol)):
                if start in self.transitions and w in self.transitions[start]:
                    for s in self.transitions[start][w]:
                        graph.edge(str(start), str(s), label=str(w))

        return graph

    # get the epsilon closure of a state using BFS
    def epsilonClosure(self, state):
        if (state not in self.transitions) or (self.lambdaSymbol not in self.transitions[state]):
            return [state]

        nextStates = set([state])
        stateQueue = deque([state])
        while len(stateQueue) > 0:
            s = stateQueue.popleft()
            if (self.lambdaSymbol not in self.transitions[s]):
                continue
            for adj in self.transitions[s][self.lambdaSymbol]:
                if adj not in nextStates:
                    nextStates.add(adj)
                    stateQueue.append(adj)
        return nextStates

    def toDFA(self):
        stateCounter = 1
        dfa_transitions = {}
        # dfa_transitions.setdefault(stateCounter, {})
        dfa_dict = {}
        dfaInitialStateTuple = tuple(self.epsilonClosure(self.initial))
        q = set()
        q.add(dfaInitialStateTuple)
        dfa_dict[dfaInitialStateTuple] = 0
        dfa_finalStatesTuples = set()
        dfa_finalStatesTuples.add(dfaInitialStateTuple)
        dfa_finalStates = []

        # if the initial state contains a final state, add intiial state to the final state of the dfa
        for i in dfaInitialStateTuple:
            if i in self.final:
                dfa_finalStates.append(0)
                break

        while len(q) > 0:
            currentStates = q.pop()
            for w in self.alphabet:
                nextStatesWithoutClosure = set()
                nextStates = set()
                # get all the states that are reachable
                # from currentStates with letter w
                for s in currentStates:
                    if s in self.transitions and w in self.transitions[s]:
                        nextStatesWithoutClosure.update(self.transitions[s][w])

                for s in nextStatesWithoutClosure:
                    nextStates.update(self.epsilonClosure(s))

                # if there are no transitions for this letter, then this state
                # must go to the trap state
                if len(nextStates) == 0:
                    nextStates.add(self.trapState)

                # create a tuple out of the list so it couold be added to
                # to the set
                nextStatesTuple = tuple(sorted(nextStates))
                if nextStatesTuple not in dfa_finalStatesTuples:
                    q.add(nextStatesTuple)
                    dfa_finalStatesTuples.add(nextStatesTuple)
                    dfa_dict[nextStatesTuple] = stateCounter
                    # if there is any finals states in nextStates
                    # add this new state to dfa final states
                    for i in nextStates:
                        if i in self.final:
                            dfa_finalStates.append(stateCounter)
                            break
                    stateCounter += 1
                dfa_transitions.setdefault(dfa_dict[currentStates], {})[w] = dfa_dict[nextStatesTuple]

        self.correspondingDFA = DFA(list(dfa_dict.values()), self.alphabet, dfa_transitions, 0, dfa_finalStates)
        return self.correspondingDFA


if __name__ == "__main__":
    argc = len(sys.argv)
    args = deque(sys.argv[1:])

    # Options:
    # write to file: -o /out/path
    # disable print to stdout: -s
    # read from stdin: -i
    # render graph to output file path: -r
    # also minimize the DFA: -m

    input_file_path = ""
    output_file_path = ""
    opt_stdout = True
    opt_stdin = False
    opt_render = False
    opt_minDFA = False
    while args:
        arg = args.popleft()
        try:
            if(arg.startswith('-')):
                options = arg[1:]
                for c in options:
                    if c == 'o':
                        output_file_path = args.popleft()
                    elif c == 's':
                        opt_stdout = False
                    elif c == 'r':
                        opt_render = True
                    elif c == 'm':
                        opt_minDFA = True
                    elif c == 'i':
                        opt_stdin = True
                    elif c == 'h':
                        print("""
Options:
    write to file: -o /out/path
    disable print to stdout: -s
    read from stdin: -i
    render graph to output file path: -r
    also minimize the DFA: -m
                        """)
            else:
                input_file_path = arg
                break
        except:
            print("Usage: python automapy.py [-sirm] [-o /path/to/output/folder] [/path/to/input/file.json]")
            exit(1)

    if opt_render and not len(output_file_path):
        print("Please specify an output folder with -o /path/to/output/folder for renders")
        exit(1)
    elif opt_stdin and len(input_file_path):
        print("Can either read from a file or read from stdin")
        exit(1)
    elif not opt_stdin and not len(input_file_path):
        print("Specify where the input comes from")
        exit(1)

    if len(input_file_path):
        data = json.load(open(input_file_path))
    else:
        data = ""
        for line in sys.stdin:
            data += line.rstrip('\n')
        data = json.loads(data)

    transitions = {}
    for currentState, inputLetter, nextStates in data["transitions"]:
        transitions.setdefault(currentState, {})[inputLetter] = nextStates

    nfa = NFA(
            data["states"],
            data["alphabet"],
            transitions,
            data["initial"],
            data["final"]
        )

    dfa = nfa.toDFA()
    if(opt_minDFA):
        mdfa = dfa.minimize()

    if(opt_stdout):
        print(nfa.toJson())
        print(dfa.toJson())
        if(opt_minDFA):
            print(mdfa.toJson())

    if(opt_render):
        nfa.visualize().render(output_file_path + "/automapy_nfa")
        dfa.visualize().render(output_file_path + "/automapy_dfa")
        if(opt_minDFA):
            mdfa.visualize().render(output_file_path + "/automapy_minDFA")

    if len(output_file_path):
        with open(output_file_path + "/automapy_nfa.json", 'w') as outfile:
            outfile.write(nfa.toJson())
            outfile.close()
        with open(output_file_path + "/automapy_dfa.json", 'w') as outfile:
            outfile.write(dfa.toJson())
            outfile.close()
        if(opt_minDFA):
            with open(output_file_path + "/automapy_minDFA.json", 'w') as outfile:
                outfile.write(mdfa.toJson())
                outfile.close()
