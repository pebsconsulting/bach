import io
import bach.io
import enum

from functools import reduce
from bach.unpack import CompiledGrammar, CompiledProduction


class ParseError(RuntimeError):
    def __init__(self, reason, pos):
        self.line   = pos.line
        self.column = pos.column
        self.reason = reason
        super().__init__("Bach Parse Error at (%d:%d): %s" % \
            (self.line, self.column, reason))



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

    def advanceColumn(self):
        self.column += 1
    
    def advanceLine(self):
        self.line += 1
        self.column = 1

    def copy(self):
        return Position(self.line, self.column)

    def __repr__(self):
        return "<bach.Position (line %d, col %d)>" % (self.line, self.column)



class Token():

    def __init__(self, semantic, lexeme, position):
        self.semantic = semantic
        self.lexeme   = lexeme
        self.position = position



class Production():

    def __init__(self, terminalIdPair, lookaheadIdPair, nonterminals, captureMode):
        self.terminalIdPair  = terminalIdPair   # Terminal Set ID, Invert?
        self.lookaheadIdPair = lookaheadIdPair  # Terminal Set ID, Invert?
        self.nonterminals    = nonterminals     # List of up to 3 NonTerminal IDs

        # capture?, capture start?, capture end?, capture semantic ID
        self.captureMode = captureMode


    def capture(self):
        return self.captureMode[0]

    def captureStart(self):
        return self.captureMode[1]

    def captureEnd(self):
        return self.captureMode[2]

    def captureAs(self):
        return CaptureSemantic(self.captureMode[3])


    def __repr__(self):
        return "bach.Production => %s%s %s, lookahead %s%s, capture %s/%s/%s as %d" % (\
            "¬" if self.terminalIdPair[1] else "",
            self.terminalIdPair[0],
            ' '.join(map(str, reversed(self.nonterminals))),
            "¬" if self.lookaheadIdPair[1] else "",
            self.lookaheadIdPair[0],
            self.captureMode[0],
            self.captureMode[1],
            self.captureMode[2],
            self.captureMode[3])


    def matchTerminalPair(self, parser, pair, char):
        
        setId, invert = pair

        # special case: None = End of File
            # terminal set "special:eof" is always defined with ID=1
        if (setId == 1):
            if char is None:
                return not invert # (invert is always False in the current grammar)
            else:
                return False
        
        if char is None:
            # otherwise, EOF is not in the set nor its inverse
            return False

        terminalSet = parser.terminalSets[setId]

        if invert:
            return not char in terminalSet
        else:
            return char in terminalSet


    def match(self, parser, current, lookahead):
        return \
            self.matchTerminalPair(parser, self.terminalIdPair, current) and \
            self.matchTerminalPair(parser, self.lookaheadIdPair, lookahead)



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
            assert self.atomaton.allowableShorthandSymbol(x.symbol), \
                "Unicode code point %d disallowed for shorthand" % ord(x.symbol)
            self.shorthands.append((x.symbol, x))

        # a string of all the shorthand symbols        
        shorthandSymbolString = reduce(lambda x, y: x + y[0], self.shorthands, "")

        # a list of all sets of terminal symbols, ordered by set ID,
        # and patched with runtime-configured values
        self.terminalSets = list(self.atomaton.terminalSets(shorthandSymbolString))

        # a string of all terminal symbols for quick membership tests
        self.terminals = ''.join(set(self.atomaton.terminals() + shorthandSymbolString))

        # a list of all production rule lists, ordered by state ID
        self.states = list(self.atomaton.states(Production))
    
        # a list of special allowable end states (in addition to None)
        self.endStates = self.atomaton.endStates


    def lex(self, reader):

        # N.B. Performance - lex() relies on `list.append(char), "".join(list)`
        # being generally the most efficient way to grow a string in Python.

        # Initialise the automaton stack with the start state (ID always 0).
        state = bach.io.stack([0])

        # An offset into the stream for user-friendly error reporting
        pos = Position(1, 0)
        startPos = None

        # a list of characters used to build a token when capturing
        capture = []
        captureAs = CaptureSemantic.none

        # Iterate over the current character and a single lookahead - LL(1)
        for (current, lookahead) in bach.io.pairwise(reader):

            # Current is always a single Unicode character, but lookahead may be
            # None iff the end of the stream is reached

            if current == '\n':
                pos.advanceLine()
            elif current == '\r':
                pass
            else:
                pos.advanceColumn()

            matchedRule = False
            currentState = state.peek()
            assert currentState is not None

            # For each production rule from this state...
            for production in self.states[currentState]:

                # See if it matches current and lookahead
                if production.match(self, current, lookahead):

                    matchedRule = True

                    if production.captureStart():
                        capture = []
                        startPos = pos.copy()
                        captureAs = production.captureAs()
                        
                    
                    if production.capture():
                        capture.append(current)

                    if production.captureEnd():
                        assert startPos is not None
                        yield (captureAs, ''.join(capture), startPos.copy(), pos.copy())
                        startPos is None

                    
                    state.pop()
                    
                    for nt in production.nonterminals:
                        state.push(nt)


            if not matchedRule:
                helpCurrent = hex(ord(current))
                helpLookahead = hex(ord(lookahead)) if lookahead is not None else 'EOF'
                raise ParseError("Unexpected input %s, %s in state %d" % \
                    (helpCurrent, helpLookahead, currentState), pos)


        # special case - e.g. allow EOF at D without trailing whitespace
        finalState = state.peek()
        if finalState is not None and finalState not in self.endStates:
            raise ParseError("Unexpected end of file in state %d" % currentState, pos)


    def parse(self, src, bufsize=bach.io.DEFAULT_BUFFER_SIZE):
        
        reader = bach.io.reader(src, bufsize)()

        for token in self.lex(reader):
            print(repr(token))
        


