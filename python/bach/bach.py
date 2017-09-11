import io
import bach.io
import bach.translate
import enum

from functools import reduce
from bach.unpack import CompiledGrammar, CompiledProduction


class ParseError(RuntimeError):
    def __init__(self, reason, startPos, endPos):
        if startPos is None: startPos = Position(-1, -1)
        self.start  = startPos
        self.end    = endPos
        self.reason = reason
        super().__init__("Bach Parse Error (at %d:%d to %d:%d): %s" % \
            (self.start.line, self.start.column, self.end.line, self.end.column, reason))



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

    def __init__(self, semantic, lexeme, start, end, state=None):
        self.semantic = semantic    # type CaptureSemantic
        self.lexeme   = lexeme      # type str
        self.start    = start       # type Position
        self.end      = end         # type Position
        self.state    = state       # type Number; for debugging

    def __repr__(self):
        return "<bach.Token %s, type %s, from %s to %s (from state %d)>" % \
            (repr(self.lexeme), self.semantic, self.start, self.end, self.state)



class Document():

    def __init__(self):
        self.label = None    # A str
        self.splitAttributes = {} # A dict of attribute names to a list of non-None str values
        self._attributes = None # A dict of attribute names to non-None str values, sequences merged with space character
        self.children   = [] # A list of Document or str children


    def toElementTree(self, etreeClass):
        # e.g. from lxml import etree as ET; document.toElementTree(ET)
        return bach.translate.toElementTree(etreeClass, self)


    def setLabel(self, label):
        assert self.label is None
        self.label = label


    def addChild(self, child):
        self.children.append(child)


    def addAttribute(self, shorthand, attributeName, attributeValue, startPos, endPos):
        assert isinstance(attributeValue, str)
        value = attributeValue.strip()

        if shorthand:
            assert not attributeName
            attributeName = shorthand

        if attributeName not in self.splitAttributes:
            self.splitAttributes[attributeName] = [value]
        else:
            self.splitAttributes[attributeName].append(value)


    @property
    def attributes(self):
        if self._attributes is None:
            self._attributes = {}
            for key, values in self.splitAttributes.items():
                self._attributes[key] = ' '.join(values)

        return self._attributes


    def __repr__(self):
        return "<bach.Document: .label=%s .attributes=%s .children=%s>" % \
            (repr(self.label), self.attributes, self.children)



class Production():

    def __init__(self, terminalIdPair, lookaheadIdPair, nonterminals, captureMode):
        self.terminalIdPair  = terminalIdPair   # Terminal Set ID, Invert?
        self.lookaheadIdPair = lookaheadIdPair  # Terminal Set ID, Invert?

        # List of up to 3 NonTerminal IDs
        # N.B. these are pushed onto the stack in reverse order!
        self.nonterminals = list(reversed(nonterminals))

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
                return not invert # invert is always False here in the current grammar
            else:
                return invert
        
        if char is None:
            return False # if EOF, its neither "in" nor "in the invert of" a character set

        terminalSet = parser.terminalSets[setId]

        if invert:
            return not char in terminalSet
        else:
            return char in terminalSet


    def match(self, parser, current, lookahead):
        return \
            self.matchTerminalPair(parser, self.terminalIdPair, current) and \
            self.matchTerminalPair(parser, self.lookaheadIdPair, lookahead)


class Parser():
    atomaton = CompiledGrammar()

    def __init__(self, shorthands={}):
        """Configure and construct a new parser for a Bach document.

        Pass a dict of shorthand charater => expanded string as the second
        parameter to extend the syntax of the parser with custom shorthand
        attributes."""

        # Construct a table for runtime-configurable shorthand syntax
        # as a mapping of shorthand symbol to Shorthand objects
        self.shorthands = shorthands
        for symbol in shorthands:
            assert isinstance(shorthands[symbol], str)
            assert len(shorthands[symbol]) >= 1, \
                "Shorthand expansions may not be empty"
            assert len(symbol) == 1, \
                "Shorthands must be a single (Unicode) character"
            assert self.atomaton.allowableShorthandSymbol(symbol), \
                "Unicode code point %d disallowed for shorthand" % ord(symbol)
            assert all(map(self.atomaton.allowableShorthandSymbol, shorthands[symbol])), \
                "Unicode code point disallowed for shorthand expansion (of shorthand with code point %d)" % ord(symbol)

        # a string of all the shorthand symbols        
        self.shorthandSymbolString = ''.join(shorthands)

        # a list of all sets of terminal symbols, ordered by set ID,
        # and patched with runtime-configured values
        self.terminalSets = list(self.atomaton.terminalSets(self.shorthandSymbolString))

        # a string of all terminal symbols for quick membership tests
        self.terminals = ''.join(set(self.atomaton.terminals() + self.shorthandSymbolString))

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

            #print("Lexer state %s" % repr(state.peek()), " stack " + repr(state.entries))
            #print(current, lookahead)

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

                    #print("Match: " + repr(production))

                    matchedRule = True

                    if production.captureStart():
                        capture = []
                        startPos = pos.copy()
                        captureAs = production.captureAs()
                    
                    if production.capture():
                        capture.append(current)

                    if production.captureEnd():
                        assert startPos is not None
                        yield Token(captureAs, ''.join(capture), startPos.copy(), pos.copy(), currentState)
                        startPos = None

                    
                    state.pop()
                    
                    for nt in production.nonterminals:
                        state.push(nt)

                    # Check that our grammar isn't ambiguous!
                    """
                    for production2 in self.states[currentState]:
                        if production == production2: continue
                        if production2.match(self, current, lookahead):
                            print("Warning: ambiguous production in state %d:\n| (%d) %s\n| (%d) %s" % \
                                (currentState,
                                self.states[currentState].index(production),
                                production,
                                self.states[currentState].index(production2),
                                production2)
                            )
                    """

                    # In case it is ambiguous, use the first rule
                    break


            if not matchedRule:
                helpCurrent = hex(ord(current))
                helpLookahead = hex(ord(lookahead)) if lookahead is not None else 'EOF'
                raise ParseError("Unexpected input %s, %s in state %d" % \
                    (helpCurrent, helpLookahead, currentState), startPos, pos)


        # special case - e.g. allow EOF at D without trailing whitespace
        finalState = state.peek()
        if finalState is not None and finalState not in self.endStates:
            raise ParseError("Unexpected end of file in state %d" % finalState, startPos, pos)


    def parse(self, src, bufsize=bach.io.DEFAULT_BUFFER_SIZE):
        
        reader = bach.io.reader(src, bufsize)()
        tokens = self.lex(reader)

        # Initialise a stack of documents for parsing into a tree-type structure
        # The first document opens implicitly
        state = bach.io.stack([Document()])

        # For each classified token and a single lookahead in advance
        it = bach.io.pairwise(tokens)
        for token, lookahead in it:

            #print("Token, lookahead:")
            #print(repr(token))
            #print(repr(lookahead))
            #print("---")

            if token.semantic is CaptureSemantic.label:
                state.peek().setLabel(token.lexeme)

            elif token.semantic is CaptureSemantic.literal:
                state.peek().addChild(token.lexeme)

            elif token.semantic is CaptureSemantic.subdocStart:
                # open a new subdocument
                d = Document()
                state.peek().addChild(d)
                state.push(d)

            elif token.semantic is CaptureSemantic.subdocEnd:
                d = state.pop()
                assert d is not None # should be already enforced by grammar
        
            elif token.semantic is CaptureSemantic.attribute:

                if lookahead and lookahead.semantic is CaptureSemantic.assign:
                    _, _ = next(it)
                    value, _ = next(it)

                    # should be already enforced by grammar
                    assert value.semantic is CaptureSemantic.literal

                    state.peek().addAttribute(
                        None, token.lexeme, value.lexeme, token.start, value.end)

                else:
                    # No assignment - attribute with empty value
                    state.peek().addAttribute(
                        None, token.lexeme, "", token.start, token.end)
                    pass
        
            elif token.semantic is CaptureSemantic.shorthandSymbol:

                # should already be enforced by grammar
                assert token.lexeme in self.shorthandSymbolString
                assert lookahead and lookahead.semantic is CaptureSemantic.shorthandAttrib, \
                    "%s: lookahead (%s) is an unexpected %s" % (token.lexeme, lookahead.lexeme, str(lookahead.semantic))

                shorthand = self.shorthands[token.lexeme]
                attrib, _ = next(it)

                state.peek().addAttribute(shorthand, None, attrib.lexeme, token.start, attrib.end)

            else:
                raise ParseError("Unexpected %s" % token.semantic, token.start, token.end)


        # Return the root document
        return state.peek(0)


