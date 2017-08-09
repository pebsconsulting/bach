import io
import bach.io
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

    def __init__(self, semantic, lexeme, start, end):
        self.semantic = semantic    # type CaptureSemantic
        self.lexeme   = lexeme      # type str
        self.start    = start       # type Position
        self.end      = end         # type Position

    def __repr__(self):
        return "<bach.Token %s, type %s, from %s to %s>" % \
            (repr(self.lexeme), self.semantic, self.start, self.end)



class Document():

    def __init__(self):
        self.label = None    # A str
        self.attributes = {} # A dict of names to a list of values non-None str
        self.children   = [] # A list of Document or str children


    def setLabel(self, label):
        assert self.label is None
        self.label = label


    def addChild(self, child):
        self.children.append(child)


    def addAttribute(self, shorthand, attributeName, attributeValue, startPos, endPos):

        assert isinstance(attributeValue, str)

        if shorthand:
            attributeName = shorthand.expansion

        if attributeName not in self.attributes:
            self.attributes[attributeName] = []
        
        if shorthand:

            # Values can occur multiple times in a list
            if shorthand.collectionType is list:
                pass # OK!

            # Values can occur only once in a set
            elif shorthand.collectionType is set:
                if attributeValue in self.attributes[attributeName]:
                    return # already in set, skip to success

            # Only one value is permitted for this attribute
            elif shorthand.collectionType is None:
                if len(self.attributes[attributeName]):
                    raise BachParseError(
                        "Multiple values not allowed for this shorthand attribute",
                        startPos, endPos)
            
            else:
                # should never happen
                raise TypeError("Unknown shorthand.collectionType")


        self.attributes[attributeName].append(attributeValue)
        return True


    def __repr__(self):
        return "<bach.Document: %s %s %s>" % \
            (self.label, self.attributes, self.children)



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
                return not invert # (invert is always False here in the current grammar)
            else:
                return invert
        
        if char is None:
            return invert # ??

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

        # TODO ensure resuting expansion is always parseable
        # e.g. expansion "." => "class" is good
        # e.g. expansion "!" => 'foo="bar" foo=' is weird



class Parser():
    atomaton = CompiledGrammar()

    def __init__(self, shorthands=[]):
        """Configure and construct a new parser for a Bach document.

        Pass a list of bach.Shorthand objects as the second parameter to extend
        the syntax of the parser with custom shorthand attributes."""

        # Construct a table for runtime-configurable shorthand syntax
        # as a mapping of shorthand symbol to Shorthand objects
        self.shorthands = {}
        for x in shorthands:
            assert not x.symbol in self.shorthands, \
                "Duplicate shorthand symbol specified"
            assert self.atomaton.allowableShorthandSymbol(x.symbol), \
                "Unicode code point %d disallowed for shorthand" % ord(x.symbol)
            self.shorthands[x.symbol] = x

        # a string of all the shorthand symbols        
        shorthandSymbolString = reduce(lambda x, y: x + y[0], self.shorthands, "")
        self.shorthandSymbolString = str(shorthandSymbolString)

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
                        yield Token(captureAs, ''.join(capture), startPos.copy(), pos.copy())
                        startPos = None

                    
                    state.pop()
                    
                    for nt in production.nonterminals:
                        state.push(nt)


            if not matchedRule:
                helpCurrent = hex(ord(current))
                helpLookahead = hex(ord(lookahead)) if lookahead is not None else 'EOF'
                raise ParseError("Unexpected input %s, %s in state %d" % \
                    (helpCurrent, helpLookahead, currentState), startPos, pos)


        # special case - e.g. allow EOF at D without trailing whitespace
        finalState = state.peek()
        if finalState is not None and finalState not in self.endStates:
            raise ParseError("Unexpected end of file in state %d" % currentState, startPos, pos)


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
                        None, token.lexeme, "", token.startPos, token.endPos)
                    pass
        
            elif token.semantic is CaptureSemantic.shorthandSymbol:

                # should already be enforced by grammar
                assert token.lexeme in self.shorthandSymbolString
                assert lookahead and lookahead.semantic is CaptureSemantic.shorthandAttrib

                shorthand = parser.shorthands[token.lexeme]
                attrib, _ = next(it)

                state.peek().addAttribute(shorthand, None, attrib.lexeme, token.start, attrib.end)

            else:
                raise BachParseError("Unexpected %s" % token.semantic, token.start, token.end)


        # Return the root document
        return state.peek(0)

