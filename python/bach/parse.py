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
        super().__init__("%s at line %d column %d (abs %d)" % \
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
        if not c: raise StopIteration # EOF
        yield c


@unique
class ProductionSymbol(Enum):
    S      =  0 # Start
    IWS    =  1 # "inline" whitespace - whitespace excluding \n
    LF     =  2 # Linefeed
    C      =  3 # Comment
    LSQ    =  4 # 'Single'-Quoted String Literal Remainder (excudes opening quote)
    LDQ    =  5 # "Double"-Quoted String Literal Remainder (excudes opening quote)
    LBQ    =  6 # [Bracket]-Quoted String Literal Remainder (excudes opening quote)
    LSQESC =  7 # Escape Sequence within 'Single'-Quoted String Literal Remainder
    LDQESC =  8 # Escape Sequence within "Double"-Quoted String Literal Remainder
    LBQESC =  9 # Escape Sequence within [Bracket]-Quoted String Literal Remainder
    
    @staticmethod
    def fromString(s):
        return ProductionSymbol[s]




class TerminalSet():
    @staticmethod
    def contains(collection, element):
        if element is None: return False
        if collection is True: return True  # All
        if collection == '': return False # Empty
        return element in collection

    sets = {
        # All - special set of all valid characters
        'All': True,
        # Empty - special set of no characters
        'Empty': '',
        # iws - "inline whitespace" - whitespace excluding \n
        'iws': '\t\r ',
        # ws - whitespace
        'ws': '\t\r\n ',
        # lf - linefeed
        'lf': '\n',
        # bs - backslash
        'bs': '\\',
        # ss -  Shorthand Seperator
        'ss': '#.*^?!@|~$',
        # sc -  Special Character
        'sc': '#.*^?!@|~$=\t\r\n ()[]{}<>"\'\\/',
        # oqt - Opening Quote
        'oqt': '"\'[{<)'
    }
    
    @staticmethod
    def fromString(s):
        return TerminalSet.sets.get(s)


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
        
        rules[i] = (productionSymbol, currentCharIn, currentCharNotIn, \
            lookaheadIn, lookaheadNotIn, restOfRule, ruleFlags)
    
    return rules



ProductionRules = resolveParserRules([\
    # Each rule is a tuple:    
    # - production symbol,
    # - current character in TerminalSet?
    # - current character not in TerminalSet?
    # - lookahead in TerminalSet?
    # - lookahead not in TerminalSet?
    # - rest of rule (array of ProductionSymbols),
    # - ParserRuleFlags (add together)
    
    # Use 'A' for ProductionSymbol.A
    # Use 'ϵname' for a named TerminalSet.name, 'abc' for the literals a|b|c
    # Use 'name' for ParserRuleFlag.name
    # Use 'name1+name2' for ParserRuleFlag.name1 + ParserRuleFlag.name2

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
    # C => ~lf
    ('C',      'ϵAll', 'ϵlf',    'ϵlf',  'ϵEmpty', [],                      []),
    # C => ~lf C
    ('C',      'ϵAll', 'ϵlf',    'ϵAll', 'ϵlf',    ['C'],                   []),
    
    # Rules for 'Single'/"Double"/[bracket]-quoted literals
    
    # S   => " LDQ
    ('S',      '\'',   'ϵEmpty', 'ϵAll', 'ϵEmpty', ['LSQ', 'S'],            ['captureStart']),
    ('S',      '"',    'ϵEmpty', 'ϵAll', 'ϵEmpty', ['LDQ', 'S'],            ['captureStart']),
    ('S',      '[',    'ϵEmpty', 'ϵAll', 'ϵEmpty', ['LBQ', 'S'],            ['captureStart']),
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
    
    # ??? for rules with a common prefix, have an extra tuple element,
    # that makes a list of rules that can apply only at that stage
    # ??? for rules that capture, have an extra tuple flags element
    # ??? compact and preprocess the rules (e.g. reverse in advance)
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
        col = 1
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
                    if ParserRuleFlag.captureEnd in ruleFlags:
                        print("capture: "+''.join(capture))
                    if ParserRuleFlag.capture in ruleFlags:
                        capture.append(current)
                
                state.pop()
                
                for i in reversed(restOfRule):
                    state.push(i)
               
                #print("Rule matched! " + str(rule))
                continue # NOTE could check no other rules match
        
        if match is None:
            if symbol is not ProductionSymbol.S:
                print("Syntax Error")
            return
        
        
        
        


