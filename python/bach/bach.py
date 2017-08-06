import io
import bach.io
import enum

from functools import reduce
from bach.unpack import CompiledGrammar, CompiledProduction



@enum.unique
class CaptureSemantic(enum.Enum):
    """Semantics captured at the level of the grammar that lets us know how
       a token should be used depending on the state of the lexer at the time
       it was captured."""

#   -- The numbers MUST match the section [Capture Semantics] in grammar.txt

    none            = 0
    label           = 1
    attribute       = 2
    literal         = 3
    assign          = 4
    subdocStart     = 5
    subdocEnd       = 6
    shorthandSymbol = 7
    shorthandAttrib = 8



class Position():
    def __init__(self, line, column):
        self.line = line
        self.column = column


class Token():
    def __init__(self, semantic, lexeme, position):
        self.semantic = semantic
        self.lexeme   = lexeme
        self.position = position



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
    atomaton = CompiledGrammar()

    def __init__(self, shorthands=[]):
        """Configure and construct a new parser for a Bach document.

        Pass a list of bach.Shorthand objects as the second parameter to extend
        the syntax of the parser with custom shorthand attributes."""

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
    

    def lex(self, reader):

        # N.B. Performance - lex() relies on `list.append(char), "".join(list)`
        # being generally the most efficient way to grow a string in Python.

        # Initialise the automaton stack with the start state (ID always 0).
        state = bach.io.stack([0])

        # Iterate over the current character and a single lookahead - LL(1)
        for (current, lookahead) in bach.io.pairwise(reader):
            # lookahead may be None if EOF, but current is never None

            print("%s, lookahead %s" % (repr(current), repr(lookahead)))
            continue


    def parse(self, src, bufsize=bach.io.DEFAULT_BUFFER_SIZE):
        
        reader = bach.io.reader(src, bufsize)()
        tokens = self.lex(reader)
        


