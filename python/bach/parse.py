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
    """Non-terminal symbols that appear in production rules"""
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
    D      = 11 # Document (i.e. past function label and any header comments)
    LD     = 12 # Literal followed by rest of D
    ALD    = 13 # Assignment followed by LD
    XSCC   = 14 # Excluding Special Characters Capture
    SDS    = 15 # Subdocument Start (excludes opening parenthesis)
    SD     = 16 # Subdocument (i.e. past function label)
    
    @staticmethod
    def fromString(s):
        return ProductionSymbol[s]


@unique
class CaptureSemantic(Enum):
    """Semantics captured at the level of the grammar"""
    none        = 0
    label       = 1
    attribute   = 2
    literal     = 3
    assign      = 4
    subdocStart = 5
    subdocEnd   = 6
    
    @staticmethod
    def fromString(s):
        return CaptureSemantic[s]


class TerminalSet():
    """Terminal symbols that appear in production rules"""
    # we use strings here to represent the concept of "a set of characters"
    
    # The special character `None` may be generated by a lookahead past the end
    # of the document.
    
    All   = True         # special set of all valid chars - excl. None value
    Empty = ''           # empty set - does not include the None value
    Eof   = None         # special set of only the None value
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
    """Semantic annotations for each rule e.g. for lexeme output"""
    captureStart = 1
    captureEnd   = 2
    capture      = 3
    
    @staticmethod
    def fromString(s):
        if not s: return 0
        return ParserRuleFlag[s]


def buildParserRules(rules):
    """Given parser rules specified using a shorthand notation, expand each
       into the proper form and sort for efficient processing."""
       
    def resolveTerminalSet(s):
        # Given a string 'ϵname', '∉name', 'ϵabc', '∉abc', where 'name' is
        # the name of a TerminalSet, or a plain sequence of characters,
        # return a 2-tuple: (inCharacterSet, notInCharacterSet) such that a
        # character matching both conditions satisfies the rule in our notation.
    
        if s and (s[0] == 'ϵ'):
            try:
                return (TerminalSet.fromString(s[1:]), TerminalSet.Empty)
            except AttributeError:
                return (s[1:], TerminalSet.Empty)
        elif s and (s[0] == '∉'):
            try:
                return (TerminalSet.All, TerminalSet.fromString(s[1:]))
            except AttributeError:
                return (TerminalSet.All, s[1:])
        else:
            raise Exception('Invalid rule '+repr(s))
    
    # Given rules in our notation, resolve strings into values we can use
    for i in range(len(rules)):
        productionSymbol, currentCharMatch, lookaheadCharMatch, \
            restOfRule, ruleFlags, emitSemantic = rules[i]
        
        productionSymbol = ProductionSymbol.fromString(productionSymbol)
        currentCharIn, currentCharNotIn = resolveTerminalSet(currentCharMatch)
        lookaheadIn, lookaheadNotIn = resolveTerminalSet(lookaheadCharMatch)
        restOfRule = list(map(ProductionSymbol.fromString, restOfRule))
        ruleFlags = list(map(ParserRuleFlag.fromString, ruleFlags))
        emitSemantic = CaptureSemantic.fromString(emitSemantic)
        
        # matching rules are pushed on the stack in reverse order
        restOfRule       = list(reversed(restOfRule))
        
        rules[i] = (productionSymbol, currentCharIn, currentCharNotIn, \
            lookaheadIn, lookaheadNotIn, restOfRule, ruleFlags, emitSemantic)
    
    # sort so that rules with the same symbol are grouped together
    rules.sort(key=lambda x: x[0].value)
    
    # to efficiently lookup all possible rules from a given symbol,
    # build an index from symbol -> (firstRuleIndex, lastRuleIndex)
    index = {}
    for i in range(len(rules)):
        symbol, _, _, _, _, _, _, _ = rules[i]
        if symbol in index:
            index[symbol] = (index[symbol][0], i)
        else:
            index[symbol] = (i, i)
    
    return (index, rules)



def productionRulesBySymbol(ruledata, symbol):
    """Generator function that yields only rules starting with a certain symbol"""
    index, rules = ruledata
    left, right = index[symbol]
    for i in range(left, right+1):
        yield rules[i]


ProductionRules =  buildParserRules([\
    # These rules are very thorough because we are able to efficiently enforce
    # much of the semantics at the level of the language grammar itself.
    # All production rules are given in Greibach Normal Form, with one
    # character of lookahead to resolve ambiguities, i.e. LL(1).

    # Each rule is a tuple:
    # - Production Symbol,
    # - current character matches TerminalSet? (ϵ/∉)
    # - lookahead character matches TerminalSet? (ϵ/∉)
    # - rest of rule (list of ProductionSymbols),
    # - flags (list of ParserRuleFlags)
    # - capture semantic
    
    # Use 'A' for ProductionSymbol.A
    # Use 'ϵname' for In named TerminalSet.name, 'ϵabc' for In set ('a','b','c')
    # Use '∉name' for Not In named TerminalSet.name, '∉abc' for Not In set ('a','b','c')
    # Use 'name' for a ParserRuleFlag.name
    # Use 'name' for CaptureSemantic.name

    # --- Rules for initial whitespace and comments at head of document
    
    # S => iws LF S
    ('S',      'ϵiws',      'ϵlf',      ['LF', 'S'],            [], 'none'),
    # S => iws IWS LF S
    ('S',      'ϵiws',      '∉lf',      ['IWS', 'LF', 'S'],     [], 'none'),
    # IWS => iws
    ('IWS',    'ϵiws',      '∉iws',     [],                     [], 'none'),
    # IWS => iws IWS
    ('IWS',    'ϵiws',      'ϵiws',     ['IWS'],                [], 'none'),
    # S => lf S
    ('S',      'ϵlf',       'ϵAll',     ['S'],                  [], 'none'),
    # LF => lf
    ('LF',     'ϵlf',       'ϵAll',     [],                     [], 'none'),
    # S => # C LF S
    ('S',      'ϵ#',        '∉lf',      ['C', 'LF', 'S'],       [], 'none'),
    # S => # LF S
    ('S',      'ϵ#',        'ϵlf',      ['LF', 'S'],            [], 'none'),
    # C => ¬lf
    ('C',      '∉lf',       'ϵlf',      [],                     [], 'none'),
    # C => ¬lf C
    ('C',      '∉lf',       '∉lf',      ['C'],                  [], 'none'),
    
    
    # --- Rules for strings of "one or more" in a certain character set
    
    # WS => ws
    ('WS',     'ϵws',       '∉ws',      [],                     [], 'none'),
    # WC => ws WS
    ('WS',     'ϵws',       'ϵws',      [],                     [], 'none'),
    # WC => ws, then EOF
    ('WS',     'ϵws',       'ϵEof',     [],                     [], 'none'),
    
    # XSCC => ¬sc
    ('XSCC',    '∉sc',      'ϵsc',      [],                     ['captureEnd', 'capture'],                  'none'),
    # XSCC => ¬sc XSCC
    ('XSCC',    '∉sc',      '∉sc',      ['XSCC'],               ['capture'],                                'none'),
    
    
    # --- Start of document, a function/label identifier on the first line
    
    # S => ¬sc WS D
    ('S',       '∉sc',      'ϵws',      ['WS', 'D'],            ['captureStart', 'captureEnd', 'capture'],  'label'),
    # S => ¬sc XSCC D
    ('S',       '∉sc',      '∉sc',      ['XSCC','D'],           ['captureStart', 'capture'],                'label'),
    
    
    # --- Document may contain arbitrary whitespace

    # D => ws D
    ('D',       'ϵws',      '∉ws',      ['D'],                  [], 'none'),
    # D => ws WS D
    ('D',       'ϵws',      'ϵws',      ['WS', 'D'],            [], 'none'),
    # D => ws, lookahead EOF - special case of end of document
    ('D',       'ϵws',      'ϵEof',     [],                     [], 'none'),
    
    
    # --- Attributes - standalone
    # (may be the start of a pair, but that can't yet be detected)
    
    # D => ¬sc WS D
    ('D',       '∉sc',      'ϵws',      ['WS', 'D'],            ['captureStart', 'captureEnd', 'capture'],  'attribute'),
    # D => ¬sc XSCC D
    ('D',       '∉sc',      '∉sc',      ['XSCC','D'],           ['captureStart', 'capture'],                'attribute'),
    
    
    # --- Attributes - pair start / pair second half
    
    # D => ¬sc asgn LD
    ('D',       '∉sc',      'ϵasgn',    ['ALD'],                ['captureStart', 'captureEnd', 'capture'],  'attribute'),
    # D => assgn LD
    ('D',       'ϵasgn',    'ϵAll',     ['LD'],                 ['captureStart', 'captureEnd', 'capture'],  'assign'),
    # ALD => assign LD
    ('ALD',     'ϵasgn',    'ϵAll',     ['LD'],                 [],                                         'attribute'),
    # LD => ws LD
    ('LD',      'ϵws',      'ϵAll',     ['LD'],                 [],                                         'none'),
    
    
    # --- Subdocuments Start
    
    # D => ( SDS D
    ('D',       'ϵ(',       'ϵAll',     ['SDS', 'D'],           ['captureStart', 'captureEnd', 'capture'],  'subdocStart'),
    # SDS => ws SDS
    ('SDS',      'ϵws',      'ϵAll',     ['SDS'],               [],                                         'none'),
    
    # --- Start of subdocument, a function/label identifier on the first line
    
    # SDS => ¬sc WS SD
    ('SDS',     '∉sc',      'ϵws',      ['WS', 'SD'],           ['captureStart', 'captureEnd', 'capture'],  'label'),
    # SDS => ¬sc XSCC SD
    ('SDS',     '∉sc',      '∉sc',      ['XSCC','SD'],          ['captureStart', 'capture'],                'label'),
    
    # --- Rest of subdocument
    
    # SD => ( SDS SD
    ('SD',      'ϵ(',       'ϵAll',     ['SDS', 'SD'],          ['captureStart', 'captureEnd', 'capture'],  'subdocStart'),
    # SD => )
    ('SD',      'ϵ)',       'ϵAll',     [],                     ['captureStart', 'captureEnd', 'capture'],  'subdocEnd'),
    # SD => ws SD
    ('SD',      'ϵws',      'ϵAll',     ['SD'],                 [],                                         'none'),


    # --- Rules for 'Single'/"Double"/[bracket]-quoted literals and escapes
    
    # D   => " LDQ D
    ('D',       'ϵ\'',      'ϵAll',     ['LSQ', 'D'],           ['captureStart'],                           'literal'),
    ('D',       'ϵ"',       'ϵAll',     ['LDQ', 'D'],           ['captureStart'],                           'literal'),
    ('D',       'ϵ[',       'ϵAll',     ['LBQ', 'D'],           ['captureStart'],                           'literal'),
    ('LD',      'ϵ\'',      'ϵAll',     ['LSQ', 'D'],           ['captureStart'],                           'literal'),
    ('LD',      'ϵ"',       'ϵAll',     ['LDQ', 'D'],           ['captureStart'],                           'literal'),
    ('LD',      'ϵ[',       'ϵAll',     ['LBQ', 'D'],           ['captureStart'],                           'literal'),
    # LDQ  => "
    ('LSQ',     'ϵ\'',      'ϵAll',     [],                     ['captureEnd'],                             'none'),
    ('LDQ',     'ϵ"',       'ϵAll',     [],                     ['captureEnd'],                             'none'),
    ('LBQ',     'ϵ]',       'ϵAll',     [],                     ['captureEnd'],                             'none'),
    # LDQ => ¬bs~" LDQ
    ('LSQ',     '∉\\\'',    'ϵAll',     ['LSQ'],                ['capture'],                                'none'),
    ('LDQ',     '∉\\"',     'ϵAll',     ['LDQ'],                ['capture'],                                'none'),
    ('LBQ',     '∉\\]',     'ϵAll',     ['LBQ'],                ['capture'],                                'none'),
    # LDQ  => bs LDQESC LDQ
    ('LSQ',     'ϵbs',      'ϵAll',     ['LSQESC', 'LSQ'],      [],                                         'none'),
    ('LDQ',     'ϵbs',      'ϵAll',     ['LDQESC', 'LDQ'],      [],                                         'none'),
    ('LBQ',     'ϵbs',      'ϵAll',     ['LBQESC', 'LBQ'],      [],                                         'none'),
    # LDQESC => bs | cdq
    ('LSQESC',  'ϵ\\\'',    'ϵAll',     [],                     ['capture'],                                'none'),
    ('LDQESC',  'ϵ\\"',     'ϵAll',     [],                     ['capture'],                                'none'),
    ('LBQESC',  'ϵ\\]',     'ϵAll',     [],                     ['capture'],                                'none'),
])


class ParserState:
    def __init__(self):
        # a stack to keep track of
        # 1. the current production symbol
        # 2. the rule chosen
        # 3. how much of the rule we've done
        self.stack = [ProductionSymbol.S]
    
    def top(self):
        return self.stack[-1]
    
    def pop(self):
        #print("Pop Symbol")
        self.stack.pop()
    
    def push(self, nextSymbol):
        #print("Push Symbol %s" % nextSymbol)
        self.stack.append(nextSymbol)


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

    currentSemantic = None

    for (current, lookahead) in pairwise(streamToGenerator(stream)):
        pos = setpos(pos, current)
        
        match = None
        
        try:
            top = state.top()
        except IndexError:
            raise BachSyntaxError("Expected: end of file", pos)
        symbol = top
        #print("symbol=%s, current=%s, lookahead=%s, pos=%s, d %d" % (repr(symbol), repr(current), repr(lookahead), pos, len(state.stack)))
    
        for rule in productionRulesBySymbol(ProductionRules, symbol):
            ruleSymbol, ruleCurrentIn, ruleCurrentNotIn, ruleLookaheadIn, \
            ruleLookaheadNotIn, restOfRule, ruleFlags, emitSemantic = rule
            
            if  (TerminalSet.contains(ruleCurrentIn, current)) and \
                (not TerminalSet.contains(ruleCurrentNotIn, current)) and \
                (TerminalSet.contains(ruleLookaheadIn, lookahead)) and \
                (not TerminalSet.contains(ruleLookaheadNotIn, lookahead)):

                match = rule
                
                if ruleFlags:
                    if ParserRuleFlag.captureStart in ruleFlags:
                        capture = []
                        currentSemantic = emitSemantic
                    if ParserRuleFlag.capture in ruleFlags:
                        capture.append(current)
                    if ParserRuleFlag.captureEnd in ruleFlags:
                        print("capture: %s as %s" % (repr(''.join(capture)), currentSemantic))
                
                state.pop()
                
                for i in restOfRule:
                    state.push(i)
               
                #print("Rule matched! " + str(rule))
                continue # NOTE could check no other rules match
        
        if match is None:
            raise BachSyntaxError("unexpected "+repr(current), pos)
            return
        
        
        
        


