from functools import reduce
from bach.unpack import CompiledGrammar, CompiledProduction


class Production():
    def __init__(self, terminalIdPair, lookaheadIdPair, nonterminals, captureMode):
        self.terminalIdPair = terminalIdPair   # Terminal Set ID, Invert?
        self.lookaheadIdPair = lookaheadIdPair # Terminal Set ID, Invert?
        self.nonterminals = nonterminals       # List of up to 3 NonTerminal IDs

        # capture?, capture start?, capture end?, capture semantic ID
        self.captureMode = captureMode

    def __repr__(self):
        return "bach.Production => %s%s %s, lookahead %s%s, capture %s/%s/%s as %d" % (\
            "¬" if self.terminalIdPair[1] else "",
            self.terminalIdPair[0],
            ' '.join(map(str, self.nonterminals)),
            "¬" if self.lookaheadIdPair[1] else "",
            self.lookaheadIdPair[0],
            self.captureMode[0],
            self.captureMode[1],
            self.captureMode[2],
            self.captureMode[3])



class Shorthand():
    def __init__(self, symbol, expansion, collectionType=None, collectionSplit=" "):
        assert len(symbol) == 1, "Symbol must be a single character"
        assert collectionType in (list, set, None), "CollectionType must be List, Set, or None"
        self.symbol = symbol
        self.expansion = expansion
        self.collectionType = collectionType
        self.collectionSplit = collectionSplit


class Parser():
    sm = CompiledGrammar()

    def __init__(self, shorthands=[]):

        # Construct a table for runtime-configurable shorthand syntax
        # as a list of tuples (symbol, shorthand) with each symbol unique
        self.shorthands = []
        for x in shorthands:
            assert not (x.symbol, x) in self.shorthands, \
                "Duplicate shorthand symbol specified"
            assert self.sm.allowableShorthandSymbol(x.symbol), \
                "Unicode code point %d disallowed for shorthand" % ord(x.symbol)
            self.shorthands.append((x.symbol, x))

        # a string of all the shorthand symbols        
        shorthandSymbolString = reduce(lambda x, y: x + y[0], self.shorthands, "")

        # a list of all sets of terminal symbols, ordered by set ID,
        # and patched with runtime-configured values
        self.terminalSets = list(self.sm.terminalSets(shorthandSymbolString))

        # a string of all terminal symbols for quick membership tests
        self.terminals = ''.join(set(self.sm.terminals() + shorthandSymbolString))

        # a list of all production rule lists, ordered by state ID
        self.states = list(self.sm.states(Production))

#        for i in range(0, len(self.states)):
#            print("[STATE %d]" % i)
#            for j in self.states[i]:
#                print(j)


