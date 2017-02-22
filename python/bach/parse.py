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
class ParserSymbol(Enum): # see syntax.txt for state meanings
    S      =  0 # Start
    IWS    =  1 # "inline" whitespace - whitespace excluding \n
    LF     =  2 # Linefeed
    C      =  3 # Comment
    LSQ    =  4 # 'Single'-Quoted String Literal Remainder
    LDQ    =  5 # "Double"-Quoted String Literal Remainder
    LBQ    =  6 # [Bracket]-Quoted String Literal Remainder
    LSQESC =  7 # Escape Sequence within Single-Quoted String Literal Remainder
    LDQESC =  8 # Escape Sequence within Double-Quoted String Literal Remainder
    LBQESC =  9 # Escape Sequence within Bracket-Quoted String Literal Remainder
    




class TerminalSet:
    @staticmethod
    def contains(collection, element):
        if element is None:                 return False
        if collection is TerminalSet.All:   return True
        if collection is TerminalSet.Empty: return False
        return element in collection

    # All - special set of all valid characters
    All   = 1
    # Empty - special set of no characters
    Empty = 2
    # iws - "inline whitespace" - whitespace excluding \n
    iws = '\t\r '
    # ws - whitespace
    ws  = '\t\r\n '
    # lf - linefeed
    lf  = '\n'
    # bs - backslash
    bs = '\\'
    # ss -  Shorthand Seperator
    ss  = '#.*^?!@|~$'
    # sc -  Special Character
    sc  = '#.*^?!@|~$=\t\r\n ()[]{}<>"\'\\/'
    # oqt - Opening Quote
    oqt = '"\'[{<)'


class ParserRules:
    # production symbol,
    # current character in set,
    # current character not in set,
    # lookahead in set,
    # lookahead not in set,
    # rest of rule (array)
    rules = [\
        # S => iws LF S
        (ParserSymbol.S,      TerminalSet.iws, TerminalSet.Empty, TerminalSet.lf,  TerminalSet.Empty, [ParserSymbol.LF, ParserSymbol.S]),
        # S => iws IWS LF S
        (ParserSymbol.S,      TerminalSet.iws, TerminalSet.Empty, TerminalSet.All, TerminalSet.lf,    [ParserSymbol.IWS, ParserSymbol.LF, ParserSymbol.S]),
        # IWS => iws
        (ParserSymbol.IWS,    TerminalSet.iws, TerminalSet.Empty, TerminalSet.All, TerminalSet.iws,   []),
        # IWS => iws IWS
        (ParserSymbol.IWS,    TerminalSet.iws, TerminalSet.Empty, TerminalSet.iws, TerminalSet.Empty, [ParserSymbol.IWS]),
        # S => lf S
        (ParserSymbol.S,      TerminalSet.lf,  TerminalSet.Empty, TerminalSet.All, TerminalSet.Empty, [ParserSymbol.S]),
        # LF => lf
        (ParserSymbol.LF,     TerminalSet.lf,  TerminalSet.Empty, TerminalSet.All, TerminalSet.Empty, []),
        # S => # C LF S
        (ParserSymbol.S,      ('#'),           TerminalSet.Empty, TerminalSet.All, TerminalSet.lf,    [ParserSymbol.C, ParserSymbol.LF, ParserSymbol.S]),
        # S => # LF S
        (ParserSymbol.S,      ('#'),           TerminalSet.Empty, TerminalSet.lf,  TerminalSet.Empty, [ParserSymbol.LF, ParserSymbol.S]),
        # C => ~lf
        (ParserSymbol.C,      TerminalSet.All, TerminalSet.lf,    TerminalSet.lf,  TerminalSet.Empty, []),
        # C => ~lf C
        (ParserSymbol.C,      TerminalSet.All, TerminalSet.lf,    TerminalSet.All, TerminalSet.lf,    [ParserSymbol.C]),
        
        # S   => " LDQ
        (ParserSymbol.S,      ('"'),           TerminalSet.Empty, TerminalSet.All, TerminalSet.Empty, [ParserSymbol.LDQ, ParserSymbol.S]),
        # LDQ  => "
        (ParserSymbol.LDQ,    ('"'),           TerminalSet.Empty, TerminalSet.All, TerminalSet.Empty, []),
        # LDQ => ¬bs~" LDQ
        (ParserSymbol.LDQ,    TerminalSet.All, ('\\', '"'),       TerminalSet.All, TerminalSet.Empty, [ParserSymbol.LDQ]),
        # LDQ  => bs LDQESC LDQ
        (ParserSymbol.LDQ,    TerminalSet.bs,  TerminalSet.Empty, TerminalSet.All, TerminalSet.Empty, [ParserSymbol.LDQESC, ParserSymbol.LDQ]),
        # LDQESC => bs | cdq
        (ParserSymbol.LDQESC, ('\\', '"'),     TerminalSet.Empty, TerminalSet.All, TerminalSet.Empty, []),
        
        # ??? for rules with a common prefix, have an extra tuple element,
        # that makes a list of rules that can apply only at that stage
        # ??? for rules that capture, have an extra tuple flags element
        # ??? compact and preprocess the rules (e.g. reverse in advance)
    ]


class ParserState:
    def __init__(self):
        # a stack to keep track of
        # 1. the current production symbol
        # 2. the rule chosen
        # 3. how much of the rule we've done
        self.stack = [(ParserSymbol.S, 0, 0)]
    
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
    
        for rule in ParserRules.rules:
            ruleSymbol, ruleCurrentIn, ruleCurrentNotIn, ruleLookaheadIn, \
            ruleLookaheadNotIn, restOfRule = rule
            
            if  (symbol == ruleSymbol) and \
                (TerminalSet.contains(ruleCurrentIn, current)) and \
                (not TerminalSet.contains(ruleCurrentNotIn, current)) and \
                (TerminalSet.contains(ruleLookaheadIn, lookahead)) and \
                (not TerminalSet.contains(ruleLookaheadNotIn, lookahead)):

                match = rule
                
                state.pop()
                
                for i in reversed(restOfRule):
                    state.push(i)
               
                #print("Rule matched! " + str(rule))
                continue # NOTE could check no other rules match
        
        if match is None:
            #state.pop()
            #break
            if symbol is not ParserSymbol.S:
                print("Syntax Error")
            return
        
        
        
        


