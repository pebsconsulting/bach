# Bach - a general-purpose semantic document markup language
#
# Copyright © 2017 Ben Golightly <ben@tawesoft.co.uk>
# Copyright © 2017 Tawesoft Ltd <opensource@tawesoft.co.uk>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction,  including without limitation the rights
# to use,  copy, modify,  merge,  publish, distribute, sublicense,  and/or sell
# copies  of  the  Software,  and  to  permit persons  to whom  the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice  and this permission notice  shall be  included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED  "AS IS",  WITHOUT WARRANTY OF ANY KIND,  EXPRESS OR
# IMPLIED,  INCLUDING  BUT  NOT LIMITED TO THE WARRANTIES  OF  MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE  AND NONINFRINGEMENT.  IN NO EVENT SHALL THE
# AUTHORS  OR COPYRIGHT HOLDERS  BE LIABLE  FOR ANY  CLAIM,  DAMAGES  OR  OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from enum import Enum, unique
from itertools import tee, zip_longest
from functools import reduce

class BachError(Exception): pass
class BachRuntimeError(BachError): pass
class BachSyntaxError(BachRuntimeError):
    def __init__(self, message,  pos):
        line, col, offset = pos
        super().__init__("%s at line %d column %d (character %d)" % \
            (message, line, col, offset))
        self.lineno = line
        self.column = col
        self.offset = offset


def pairwise(iterable):
    """For [a, b, c, ...] lazily return [(a, b), (b, c), (c, ...), (..., None)]"""
    # simply from https://docs.python.org/3/library/itertools.html#itertools-recipes
    a, b = tee(iterable)
    next(b, None)
    return zip_longest(a, b)


def streamToGenerator(stream):
    """Lazily read a character from a stream at a time"""
    while True:
        c = stream.read(1)
        if not c: break # EOF
        yield c


@unique
class ProductionSymbol(Enum):
    S      =  0 # Start
    IWS    =  1 # "inline" whitespace - whitespace excluding \n
    WS     =  2 # whitespace
    LF     =  3 # Linefeed
    C      =  4 # Comment
    LSQ    =  5 # 'Single'-Quoted String Literal Remainder (excudes opening quote)
    LDQ    =  6 # "Double"-Quoted String Literal Remainder (excudes opening quote)
    LBQ    =  7 # [Bracket]-Quoted String Literal Remainder (excudes opening quote)
    LSQESC =  8 # Escape Sequence within 'Single'-Quoted String Literal Remainder
    LDQESC =  9 # Escape Sequence within "Double"-Quoted String Literal Remainder
    LBQESC = 10 # Escape Sequence within [Bracket]-Quoted String Literal Remainder
    D      = 11 # Document (i.e. past any header comments)
    LD     = 12 # Literal followed by rest of D
    ALD    = 13 # Assignment followed by LD
    XSCC   = 14 # Excluding Special Characters Capture
    
    @staticmethod
    def fromString(s):
        return ProductionSymbol[s]

@unique
class CaptureSemantic(Enum):
    label      = 1 # Function or Label
    attribute  = 2 # Attribute
    literal    = 3 # Literal
    
    @staticmethod
    def fromString(s):
        return CaptureSemantic[s]


class TerminalSet():
    All   = True         # special set of all valid chars - excl. empty string
    Empty = ''           # empty set - does not include empty string
    Eof   = None         # special set of only the empty / null string
    iws   = '\t\r '      # "inline" whitespace - whitespace excluding \n
    ws    = '\t\r\n '    # whitespace
    lf    = '\n'         # linefeed
    bs    = '\\'         # backslash
    ss    = '#.*^?!@|~$' # "shorthand separator"
    sc    = '#.*^?!@|~$=:\t\r\n ()[]{}<>"\'\\/' # special character
    oqt   = '"\'['       # opening quote
    asgn  = '=:'         # assignment characters
    
    @staticmethod
    def contains(collection, element):
        if collection is None:
            return True if element is None else False # Eof
        
        if element is None: return False
        if collection is True: return True  # All
        if collection == '': return False # Empty
        return element in collection
    
    @staticmethod
    def fromString(s):
        return getattr(TerminalSet, s)


@unique
class ParserRuleFlag(Enum):
    captureStart = 1
    captureEnd   = 2
    capture      = 3
    
    @staticmethod
    def fromString(s):
        if not s: return 0
        return ParserRuleFlag[s]



def resolveParserRules(rules):
    def resolveTerminalSet(s):
        if s and (s[0] == 'ϵ'):
            return TerminalSet.fromString(s[1:])
        return s
    
    for i in range(len(rules)):
        productionSymbol, currentCharIn, currentCharNotIn, lookaheadIn, \
        lookaheadNotIn, restOfRule, ruleFlags = rules[i]
        
        productionSymbol = ProductionSymbol.fromString(productionSymbol)
        currentCharIn    = resolveTerminalSet(currentCharIn)
        currentCharNotIn = resolveTerminalSet(currentCharNotIn)
        lookaheadIn      = resolveTerminalSet(lookaheadIn)
        lookaheadNotIn   = resolveTerminalSet(lookaheadNotIn)
        restOfRule       = list(map(ProductionSymbol.fromString, restOfRule))
        ruleFlags        = list(map(ParserRuleFlag.fromString, ruleFlags))
        
        # rules are pushed on the stack in reverse order
        restOfRule       = list(reversed(restOfRule))
        
        rules[i] = (productionSymbol, currentCharIn, currentCharNotIn, \
            lookaheadIn, lookaheadNotIn, restOfRule, ruleFlags)
    
    return rules



ProductionRules = resolveParserRules([\
    # These rules are very thorough because we are able to efficiently enforce
    # much of the semantics at the level of the language grammar itself.
    # All production rules are given in Greibach Normal Form, with one
    # character of lookahead to resolve ambiguities, i.e. LL(1).

    # Each rule is a tuple:
    # - production symbol,
    # - current character in TerminalSet?
    # - current character not in TerminalSet?
    # - lookahead in TerminalSet?
    # - lookahead not in TerminalSet?
    # - rest of rule (list of ProductionSymbols),
    # - flags (list of ParserRuleFlags)
    # - capture semantic
    
    # TODO - we only use one of either the InSet or NotInSet at any time
    # -- combine this into a single field with ϵ/∉.
    
    # Use 'A' for ProductionSymbol.A
    # Use 'ϵname' for a named TerminalSet.name, 'abc' for the literals a|b|c
    # Use 'name' for a ParserRuleFlag.name
    # Use 'name' for CaptureSemantic.name


    # --- Rules for initial whitespace and comments at head of document
    
    # S => iws LF S
    ('S',      'ϵiws', 'ϵEmpty', 'ϵlf',  'ϵEmpty', ['LF', 'S'],             []),
    # S => iws IWS LF S
    ('S',      'ϵiws', 'ϵEmpty', 'ϵAll', 'ϵlf',    ['IWS', 'LF', 'S'],      []),
    # IWS => iws
    ('IWS',    'ϵiws', 'ϵEmpty', 'ϵAll', 'ϵiws',   [],                      []),
    # IWS => iws IWS
    ('IWS',    'ϵiws', 'ϵEmpty', 'ϵiws', 'ϵEmpty', ['IWS'],                 []),
    # S => lf S
    ('S',      'ϵlf',  'ϵEmpty', 'ϵAll', 'ϵEmpty', ['S'],                   []),
    # LF => lf
    ('LF',     'ϵlf',  'ϵEmpty', 'ϵAll', 'ϵEmpty', [],                      []),
    # S => # C LF S
    ('S',      '#',    'ϵEmpty', 'ϵAll', 'ϵlf',    ['C', 'LF', 'S'],        []),
    # S => # LF S
    ('S',      '#',    'ϵEmpty', 'ϵlf',  'ϵEmpty', ['LF', 'S'],             []),
    # C => ¬lf
    ('C',      'ϵAll', 'ϵlf',    'ϵlf',  'ϵEmpty', [],                      []),
    # C => ¬lf C
    ('C',      'ϵAll', 'ϵlf',    'ϵAll', 'ϵlf',    ['C'],                   []),
    
    
    # --- Rules for strings of "one or more" in a certain character set
    
    # WS => ws
    ('WS',     'ϵws',  'ϵEmpty', 'ϵAll', 'ϵws',    [],                      []),
    # WC => ws WS
    ('WS',     'ϵws',  'ϵEmpty', 'ϵws',  'ϵEmpty', [],                      []),
    
    # XSCC => ¬sc
    ('XSCC',  'ϵAll', 'ϵsc',    'ϵsc',  'ϵEmpty', [],                      ['captureEnd', 'capture']),
    # XSCC => ¬sc XSCC
    ('XSCC',  'ϵAll', 'ϵsc',    'ϵAll', 'ϵsc',    ['XSCC'],                ['captureEnd', 'capture']),
    
    
    # --- Start of document, a function/label identifier on the first line
    
    # S => ¬sc WS D
    ('S',      'ϵAll', 'ϵsc',    'ϵws',  'ϵEmpty', ['WS', 'D'],             ['captureStart', 'captureEnd', 'capture']),
    # S => ¬sc XSCC D
    ('S',      'ϵAll', 'ϵsc',    'ϵAll', 'ϵsc',    ['XSCC','D'],            ['captureStart', 'capture']),
    
    
    # --- Document may contain arbitrary whitespace
    
    # D => ws D
    ('D',     'ϵws',  'ϵEmpty', 'ϵAll', 'ϵws',    ['D'],                   []),
    # D => ws WS D
    ('D',     'ϵws',  'ϵEmpty', 'ϵws',  'ϵEmpty', ['WS', 'D'],             []),
    # D => ws, lookahead EOF - special case of end of document
    ('D',     'ϵws',  'ϵEmpty', 'ϵEof', 'ϵEmpty', [], []),
    
    
    # --- Attributes - standalone
    # (may be the start of a pair, but that can't yet be detected)
    
    # D => ¬sc WS D
    ('D',      'ϵAll', 'ϵsc',    'ϵws',  'ϵEmpty', ['WS', 'D'],            ['captureStart', 'captureEnd', 'capture']),
    # D => ¬sc XSCC D
    ('D',      'ϵAll', 'ϵsc',    'ϵAll', 'ϵsc',    ['XSCC','D'],           ['captureStart', 'capture']),
    
    
    # --- Attributes - pair start / pair second half
    
    # D => ¬sc asgn LD
    ('D',      'ϵAll', 'ϵsc',    'ϵasgn','ϵEmpty', ['ALD'],                ['captureStart', 'captureEnd', 'capture']),
    # D => assgn LD
    ('D',      'ϵasgn', 'ϵEmpty','ϵAll', 'ϵEmpty', ['LD'],                 ['captureStart', 'captureEnd', 'capture']),
    # ALD => assign LD
    ('ALD',    'ϵasgn', 'ϵEmpty','ϵAll', 'ϵEmpty', ['LD'],                 []),
    
    
    # --- Attribute pair whitespace
    # LD => ws LD
    ('LD',    'ϵws',  'ϵEmpty', 'ϵAll', 'ϵws',    ['LD'],                  []),
    # LD => ws WS LD
    ('LD',    'ϵws',  'ϵEmpty', 'ϵws',  'ϵEmpty', ['WS', 'LD'],            []),
    
    
    
    # Rules for 'Single'/"Double"/[bracket]-quoted literals and escapes
    
    # D   => " LDQ D
    ('D',      '\'',   'ϵEmpty', 'ϵAll', 'ϵEmpty', ['LSQ', 'D'],            ['captureStart']),
    ('D',      '"',    'ϵEmpty', 'ϵAll', 'ϵEmpty', ['LDQ', 'D'],            ['captureStart']),
    ('D',      '[',    'ϵEmpty', 'ϵAll', 'ϵEmpty', ['LBQ', 'D'],            ['captureStart']),
    ('LD',     '\'',   'ϵEmpty', 'ϵAll', 'ϵEmpty', ['LSQ', 'D'],            ['captureStart']),
    ('LD',     '"',    'ϵEmpty', 'ϵAll', 'ϵEmpty', ['LDQ', 'D'],            ['captureStart']),
    ('LD',     '[',    'ϵEmpty', 'ϵAll', 'ϵEmpty', ['LBQ', 'D'],            ['captureStart']),
    # LDQ  => "
    ('LSQ',    '\'',   'ϵEmpty', 'ϵAll', 'ϵEmpty', [],                      ['captureEnd']),
    ('LDQ',    '"',    'ϵEmpty', 'ϵAll', 'ϵEmpty', [],                      ['captureEnd']),
    ('LBQ',    ']',    'ϵEmpty', 'ϵAll', 'ϵEmpty', [],                      ['captureEnd']),
    # LDQ => ¬bs~" LDQ
    ('LSQ',    'ϵAll', '\\\'',   'ϵAll', 'ϵEmpty', ['LSQ'],                 ['capture']),
    ('LDQ',    'ϵAll', '\\"',    'ϵAll', 'ϵEmpty', ['LDQ'],                 ['capture']),
    ('LBQ',    'ϵAll', '\\]',    'ϵAll', 'ϵEmpty', ['LBQ'],                 ['capture']),
    # LDQ  => bs LDQESC LDQ
    ('LSQ',    'ϵbs',  'ϵEmpty', 'ϵAll', 'ϵEmpty', ['LSQESC', 'LSQ'],       []),
    ('LDQ',    'ϵbs',  'ϵEmpty', 'ϵAll', 'ϵEmpty', ['LDQESC', 'LDQ'],       []),
    ('LBQ',    'ϵbs',  'ϵEmpty', 'ϵAll', 'ϵEmpty', ['LBQESC', 'LBQ'],       []),
    # LDQESC => bs | cdq
    ('LSQESC', '\\\'', 'ϵEmpty', 'ϵAll', 'ϵEmpty', [],                      ['capture']),
    ('LDQESC', '\\"',  'ϵEmpty', 'ϵAll', 'ϵEmpty', [],                      ['capture']),
    ('LBQESC', '\\]',  'ϵEmpty', 'ϵAll', 'ϵEmpty', [],                      ['capture']),
    

])

for i in ProductionRules:
    print(i)



class ParserState:
    def __init__(self):
        # a stack to keep track of
        # 1. the current production symbol
        # 2. the rule chosen
        # 3. how much of the rule we've done
        self.stack = [(ProductionSymbol.S, 0, 0)]
    
    def top(self):
        return self.stack[-1]
    
    def pop(self):
        print("Pop Symbol")
        self.stack.pop()
        if self.stack:
            symbol, rule, position = self.stack[-1]
            self.stack[-1] = (symbol, rule, position + 1)
    
    def push(self, nextSymbol):
        print("Push Symbol %s" % nextSymbol)
        self.stack.append((nextSymbol, 0, 0))
    
    def setrule(self, rule):
        symbol, _, position = self.stack[-1]
        self.stack[-1] = (symbol, rule, position)

    def cycle(self):
        # lets us cheaply loop on a right-recursive rule
        symbol, rule, position = self.stack[-1]
        self.stack[-1] = (symbol, 0, 0)


def setpos(currentPos, currentChar):
    line, col, offset = currentPos
    offset = offset + 1
    col = col + 1
    if (currentChar == '\n'):
        line = line + 1
        col = 0
    return (line, col, offset)



def parse(stream):
    state = ParserState()
    
    # a counter for line, col, absolute offset of the stream (counting from 1)
    pos = (1, 0, 0)
    
    # a list of characters making up a single token
    # e.g. the literal inside a quoted string
    capture = []

    for (current, lookahead) in pairwise(streamToGenerator(stream)):
        pos = setpos(pos, current)
        
        match = None
        try:
            top = state.top()
        except IndexError:
            raise BachSyntaxError("Expected: end of file", pos)
        symbol, rule, position = top
        print("symbol=%s, current=%s, lookahead=%s, pos=%s, d %d" % (repr(symbol), repr(current), repr(lookahead), pos, len(state.stack)))
    
        for rule in ProductionRules:
            ruleSymbol, ruleCurrentIn, ruleCurrentNotIn, ruleLookaheadIn, \
            ruleLookaheadNotIn, restOfRule, ruleFlags = rule
            
            if  (symbol == ruleSymbol) and \
                (TerminalSet.contains(ruleCurrentIn, current)) and \
                (not TerminalSet.contains(ruleCurrentNotIn, current)) and \
                (TerminalSet.contains(ruleLookaheadIn, lookahead)) and \
                (not TerminalSet.contains(ruleLookaheadNotIn, lookahead)):

                match = rule
                
                if ruleFlags:
                    if ParserRuleFlag.captureStart in ruleFlags:
                        capture = []
                    if ParserRuleFlag.capture in ruleFlags:
                        capture.append(current)
                    if ParserRuleFlag.captureEnd in ruleFlags:
                        print("capture: "+''.join(capture))
                
                state.pop()
                
                for i in restOfRule:
                    state.push(i)
               
                #print("Rule matched! " + str(rule))
                continue # NOTE could check no other rules match
        
        if match is None:
            raise BachSyntaxError("unexpected "+repr(current), pos)
            return
        
        
        
        


