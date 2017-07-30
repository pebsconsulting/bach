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

import bach
from enum import Enum, unique
from itertools import tee, zip_longest
from functools import reduce


def profile(func):
    return func


# default @profile decorator
if bach.profile:
    import builtins
    profile = builtins.__dict__.get('profile', profile)
    


class BachError(Exception): pass
class BachRuntimeError(BachError): pass
class BachParseError(BachRuntimeError): pass

class BachParseLimitError(BachParseError):
    def __init__(self, message, rule, pos):
        line, col, offset = pos
        super().__init__("%s (%s is %d) at line %d column %d (character %d).\n" % \
            (message, rule, getattr(bach, rule), line, col, offset))
        self.lineno = line
        self.column = col
        self.offset = offset

class BachSyntaxError(BachParseError):
    def __init__(self, message, state, pos):
        line, col, offset = pos
        xtra = ''
        if bach.debug:
            xtra = 'Lexter state: %s\n' % repr(state.stack)
        super().__init__("%s at line %d column %d (character %d).\n%sHelp: %s" % \
            (message, line, col, offset, xtra, lexerErrorHint(state)))
        self.lineno = line
        self.column = col
        self.offset = offset

class BachSemanticError(BachParseError):
    def __init__(self, message, state, pos):
        line, col, offset = pos
        xtra = ''
        if state and bach.debug:
            xtra = '\nParser state: %s' % repr(state.root())
        super().__init__("%s at line %d column %d (character %d).%s" % \
            (message, line, col, offset, xtra))
        self.lineno = line
        self.column = col
        self.offset = offset


@profile
def pairwise(iterable):
    """For [a, b, c, ...] lazily return [(a, b), (b, c), (c, ...), (..., None)]"""
    # simply from https://docs.python.org/3/library/itertools.html#itertools-recipes
    a, b = tee(iterable)
    next(b, None)
    return zip_longest(a, b)


@profile
def streamToGenerator(stream):
    """Lazily read a character from a stream at a time"""
    while True:
        c = stream.read(bach.bufsz)
        if len(c) == 0:
            break # EOF
        if len(c) == 1:
            yield c
            break
        for i in c:
            yield i


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
    ALD    = 13 # Attribute assignment followed by LD
    XSCC   = 14 # Excluding Special Characters Capture
    SDS    = 15 # Subdocument Start (excludes opening parenthesis)
    SD     = 16 # Subdocument (i.e. past function label)
    LSD    = 17 # Literal followed by rest of SD
    ALSD   = 18 # Attribute Assignment followed by LSD
    DSH    = 19 # Document shorthand attribute
    SDSH   = 20 # Subdocument shorthand attribute
    
    @staticmethod
    @profile
    def fromString(s):
        return ProductionSymbol[s]


@unique
class CaptureSemantic(Enum):
    """Semantics captured at the level of the grammar"""
    none            = 0
    label           = 1
    attribute       = 2
    literal         = 3
    assign          = 4
    subdocStart     = 5
    subdocEnd       = 6
    shorthandSymbol = 7
    shorthandAttrib = 8
    neverchecked    = 9
    
    @staticmethod
    @profile
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
    _sc   = '#=:\t\r\n ()[]{}<>"\'\\' # special characters (excl. shorthand separators)
    _dss  = '=:\t\r\n ()[]{}<>"\'\\'  # disallowed shorthand separators
    oqt   = '"\'['       # opening quote
    asgn  = '=:'         # assignment characters
    
    @profile
    def __init__(self, shorthandSeparators):
        for c in shorthandSeparators:
            if c in TerminalSet._dss:
                raise BachRuntimeError("Shorthand separator symbol %s is not allowed (reserved: %s)" % (repr(c), repr(TerminalSet._dss)))
        
        self.ss = ''.join(shorthandSeparators)
        self.sc = TerminalSet._sc + self.ss
    
    @staticmethod
    @profile
    def contains(collection, element):
        if collection is None:
            return True if element is None else False # Eof
        
        if element is None: return False
        if collection is True: return True  # All
        if collection == '': return False # Empty
        return element in collection
    
    @staticmethod
    @profile
    def fromString(s, customTerminalSet):
        if s == 'sc': return customTerminalSet.sc
        if s == 'ss': return customTerminalSet.ss
        return getattr(TerminalSet, s)


@unique
class ParserRuleFlag(Enum):
    """Semantic annotations for each rule e.g. for lexeme output"""
    captureStart = 1
    captureEnd   = 2
    capture      = 4
    
    @staticmethod
    @profile
    def fromString(s):
        return ParserRuleFlag[s]

    @staticmethod
    @profile
    def toValueFromString(s):
        return ParserRuleFlag[s].value
    
    @staticmethod
    @profile
    def containsCapture(f):
        return (f & ParserRuleFlag.capture.value) == ParserRuleFlag.capture.value
    
    @staticmethod
    @profile
    def containsCaptureStart(f):
        return (f & ParserRuleFlag.captureStart.value) == ParserRuleFlag.captureStart.value

    @staticmethod
    @profile
    def containsCaptureEnd(f):
        return (f & ParserRuleFlag.captureEnd.value) == ParserRuleFlag.captureEnd.value


@profile
def buildProductionRules(rules, customTerminalSet):
    """Given grammar rules specified using a shorthand notation, expand each
       into the proper form, then sort and index for efficient processing."""
   
    def resolveTerminalSet(s):
        # Given a string 'ϵname', '∉name', 'ϵabc', '∉abc', where 'name' is
        # the name of a TerminalSet, or a plain sequence of characters,
        # return a 2-tuple: (inCharacterSet, notInCharacterSet) such that a
        # character matching both conditions satisfies the rule in our notation.
        if s[0] == 'ϵ':
            try:
                return (TerminalSet.fromString(s[1:], customTerminalSet), TerminalSet.Empty)
            except AttributeError:
                return (s[1:], TerminalSet.Empty)
        elif s[0] == '∉':
            try:
                return (TerminalSet.All, TerminalSet.fromString(s[1:], customTerminalSet))
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
        ruleFlags = sum(map(ParserRuleFlag.toValueFromString, ruleFlags))
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


@profile
def productionRulesBySymbol(ruledata, symbol):
    """Returns an iterable of rules starting with a certain symbol"""
    index, rules = ruledata
    left, right = index[symbol]
    return rules[left:right+1]


ProductionRules = [\
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
    
    # --- "Shorthand" attributes
    # D => ss DSH D
    ('D',       'ϵss',      '∉sc',      ['DSH', 'D'],           ['captureStart', 'captureEnd', 'capture'],   'shorthandSymbol'),
    # DSH => ¬sc
    ('DSH',     '∉sc',      'ϵsc',      [],                     ['captureStart', 'captureEnd', 'capture'],   'shorthandAttrib'),
    # DSH => ¬sc XSCC
    ('DSH',     '∉sc',      '∉sc',      ['XSCC'],               ['captureStart', 'capture'],                 'shorthandAttrib'),
    # SD => ss SDSH SD
    ('SD',      'ϵss',      '∉sc',      ['SDSH', 'SD'],         ['captureStart', 'captureEnd', 'capture'],   'shorthandSymbol'),
    # SDSH => ¬sc
    ('SDSH',    '∉sc',      'ϵsc',      [],                     ['captureStart', 'captureEnd', 'capture'],   'shorthandAttrib'),
    # SDSH => ¬sc XSCC
    ('SDSH',    '∉sc',      '∉sc',      ['XSCC'],               ['captureStart', 'capture'],                 'shorthandAttrib'),
    
    # --- Attributes - standalone
    # (may be the start of a pair, but that can't yet be detected)
    
    # D => ¬sc WS D
    ('D',       '∉sc',      'ϵws',      ['WS', 'D'],            ['captureStart', 'captureEnd', 'capture'],  'attribute'),
    # D => ¬sc XSCC D
    ('D',       '∉sc',      '∉sc',      ['XSCC','D'],           ['captureStart', 'capture'],                'attribute'),
    # SD => ¬sc WS SD
    ('SD',       '∉sc',     'ϵws',      ['WS', 'SD'],           ['captureStart', 'captureEnd', 'capture'],  'attribute'),
    # SD => ¬sc XSCC SD
    ('SD',       '∉sc',     '∉sc',      ['XSCC','SD'],          ['captureStart', 'capture'],                'attribute'),
    # SD => ¬sc )       (end of subdocument)
    ('SD',       '∉sc',     'ϵ)',       ['SD'],                 ['captureStart', 'captureEnd', 'capture'],  'attribute'),
    
    # --- Attributes - pair start / pair second half
    
    # D => ¬sc asgn LD ---- (¬sc ALSD)
    ('D',       '∉sc',      'ϵasgn',    ['ALD'],                ['captureStart', 'captureEnd', 'capture'],  'attribute'),
    # D => assgn LD
    ('D',       'ϵasgn',    'ϵAll',     ['LD'],                 ['captureStart', 'captureEnd', 'capture'],  'assign'),
    # ALD => asign LD
    ('ALD',     'ϵasgn',    'ϵAll',     ['LD'],                 ['captureStart', 'captureEnd', 'capture'],  'assign'), # was [], "attribute", changed to fix issue #2
    # LD => ws LD
    ('LD',      'ϵws',      'ϵAll',     ['LD'],                 [],                                         'none'),
     # SD => ¬sc asgn LSD ---- (¬sc ALSD)
    ('SD',      '∉sc',      'ϵasgn',    ['ALSD'],               ['captureStart', 'captureEnd', 'capture'],  'attribute'),
    # SD => assgn LSD
    ('SD',      'ϵasgn',    'ϵAll',     ['LSD'],                ['captureStart', 'captureEnd', 'capture'],  'assign'),
    # ALSD => assign LSD
    ('ALSD',    'ϵasgn',    'ϵAll',     ['LSD'],                ['captureStart', 'captureEnd', 'capture'],  'assign'), # was [], "attribute", changed to fix issue #2
    # LSD => ws LSD
    ('LSD',     'ϵws',      'ϵAll',     ['LSD'],                [],                                         'none'),   
    
    # --- Subdocuments Start
    
    # D => ( SDS D
    ('D',       'ϵ(',       'ϵAll',     ['SDS', 'D'],           ['captureStart', 'captureEnd', 'capture'],  'subdocStart'),
    # SDS => ws SDS
    ('SDS',     'ϵws',      'ϵAll',     ['SDS'],               [],                                         'none'),
    
    # --- Start of subdocument, a function/label identifier on the first line
    
    # SDS => ¬sc WS SD
    ('SDS',     '∉sc',      'ϵws',      ['WS', 'SD'],           ['captureStart', 'captureEnd', 'capture'],  'label'),
    # SDS => ¬sc XSCC SD
    ('SDS',     '∉sc',      '∉sc',      ['XSCC','SD'],          ['captureStart', 'capture'],                'label'),
    # SDS => ¬sc )
    ('SDS',     '∉sc',      'ϵ)',       ['SD'],                 ['captureStart', 'captureEnd', 'capture'],  'label'),
    
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
    ('SD',      'ϵ\'',      'ϵAll',     ['LSQ', 'SD'],          ['captureStart'],                           'literal'),
    ('SD',      'ϵ"',       'ϵAll',     ['LDQ', 'SD'],          ['captureStart'],                           'literal'),
    ('SD',      'ϵ[',       'ϵAll',     ['LBQ', 'SD'],          ['captureStart'],                           'literal'),
    ('LSD',     'ϵ\'',      'ϵAll',     ['LSQ', 'SD'],          ['captureStart'],                           'literal'),
    ('LSD',     'ϵ"',       'ϵAll',     ['LDQ', 'SD'],          ['captureStart'],                           'literal'),
    ('LSD',     'ϵ[',       'ϵAll',     ['LBQ', 'SD'],          ['captureStart'],                           'literal'),
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
]


class LexerState:
    @profile
    def __init__(self):
        # a stack to keep track of production symbols
        self.stack = [ProductionSymbol.S]
    
    @profile
    def top(self):
        try:
            return self.stack[-1]
        except IndexError:
            return None
    
    @profile
    def pop(self):
        #print("Pop Symbol")
        self.stack.pop()
    
    @profile
    def push(self, nextSymbol):
        #print("Push Symbol %s" % nextSymbol)
        self.stack.append(nextSymbol)

    @profile
    def contains(self, symbol):
        return (symbol in self.stack)


@profile
def tokenise(stream, shorthandSymbols=[]):
    state = LexerState()
    customTerminalSet = TerminalSet(shorthandSymbols)
    rules = buildProductionRules(ProductionRules, customTerminalSet)
    
    # a counter for line, col, absolute offset of the stream (counting from 1)
    line, col, offset = (1, 0, 0)
    
    # a list of characters making up a single token
    # e.g. the literal inside a quoted string
    capture = []

    currentSemantic = None
    
    for (current, lookahead) in pairwise(streamToGenerator(stream)):
        offset += 1
        col += 1
        if (current is '\n'):
            line += 1
            col = 0
        
        match = None
        
        symbol = state.top()
        assert symbol
    
        for rule in productionRulesBySymbol(rules, symbol):
            ruleSymbol, ruleCurrentIn, ruleCurrentNotIn, ruleLookaheadIn, \
            ruleLookaheadNotIn, restOfRule, ruleFlags, emitSemantic = rule
            
            if  (TerminalSet.contains(ruleCurrentIn, current)) and \
                (not TerminalSet.contains(ruleCurrentNotIn, current)) and \
                (TerminalSet.contains(ruleLookaheadIn, lookahead)) and \
                (not TerminalSet.contains(ruleLookaheadNotIn, lookahead)):

                match = rule
                
                if ruleFlags:
                    if ParserRuleFlag.containsCaptureStart(ruleFlags):
                        capture = []
                        currentSemantic = emitSemantic
                    if ParserRuleFlag.containsCapture(ruleFlags):
                        capture.append(current)
                        if len(capture) > bach.max_lexeme_len:
                            raise BachParseLimitError("Maximum lexeme length", 'max_lexeme_len', (line, col, offset));
                    if ParserRuleFlag.containsCaptureEnd(ruleFlags):
                        yield (currentSemantic, ''.join(capture), (line, col, offset))
                
                state.pop()
                
                for i in restOfRule:
                    state.push(i)
               
                #print("Rule matched! " + str(rule))
                continue # NOTE could verify no other rules match
        
        if match is None:
            raise BachSyntaxError("unexpected "+repr(current), state, (line, col, offset))
    
    if state.top() not in [ProductionSymbol.D, None]:
        raise BachSyntaxError("unexpected end of file", state, (line, col, offset))


class Document:
    @profile
    def __init__(self):
        # document = (label, {shorthand}, {attributes}, [contents])
        self.label      = None
        self.attributes = {}
        self.contents   = []
        self.attribCount  = 0
        self.literalCount = 0
        self.subdocCount  = 0
    
    @profile
    def setLabel(self, s, pos):
        assert self.label is None
        
        if len(s) > bach.max_label_name_len:
            raise BachParseLimitError("Label name length limit exceeded", 'max_label_name_len', pos);
        
        self.label = s
        self.literalCount += 1
    
    @profile
    def addAttribute(self, s, pos, value=None):
        if len(s) > bach.max_attribute_name_len:
            raise BachParseLimitError("attribute name length limit exceeded", 'max_attribute_name_len', pos);
        
        if value and len(value) > bach.max_attribute_value_len:
            raise BachParseLimitError("attribute value length limit exceeded", 'max_attribute_value_len', pos)
        
        if self.attribCount >= bach.max_attributes_per_subdoc:
            raise BachParseLimitError("maximum number of attributes in this (sub)document reached", 'max_attributes_per_subdoc', pos)
        
        if not s in self.attributes:
            self.attributes[s] = []
        
        self.attributes[s].append(value)
        self.attribCount += 1
    
    @profile
    def addLiteral(self, s, pos):
        if len(s) > bach.max_literal_value_len:
            raise BachParseLimitError("literal value length limit exceeded", 'max_literal_value_len', pos)
        if self.literalCount >= bach.max_literals_per_subdoc:
            raise BachParseLimitError("Maximum number of literals exceeded in document %s" % repr(self.label), 'max_literals_per_subdoc', pos)
        
        self.contents.append(s)
        self.literalCount += 1
    
    @profile
    def addSubdoc(self, d, pos):
        if self.subdocCount >= bach.max_subdocuments_per_subdoc:
            raise BachParseLimitError("Maximum number of subdocuments exceeded in document %s" % repr(self.label), 'max_subdocuments_per_subdoc', pos)
        
        self.contents.append(d)
        self.subdocCount += 1
    
    @profile
    def toTuple(self):
        def f(x):
            if type(x) is str: return x
            return x.toTuple()
        
        newContents = []
        for x in self.contents:
            newContents.append(f(x))
        return (self.label, self.attributes, newContents)
    
    @profile
    def __repr__(self):
        return repr(self.toTuple())
        


class ParserState:
    @profile
    def __init__(self):
        # a tree to keep track of documents
        self.stack = [Document()]
        self.numLiterals = 0
        self.numSubdocs  = 0
    
    @profile
    def setLabel(self, s, pos):
        self.top().setLabel(s, pos)
    
    @profile
    def addLiteral(self, s, pos):
        if self.numLiterals >= bach.max_literals_globally:
            raise BachParseLimitError("maximum global literal limit exceeded", 'bach.max_literals_globally', pos)
    
        self.top().addLiteral(s, pos)
        self.numLiterals += 1
    
    @profile
    def root(self):
        return self.stack[0]

    @profile
    def top(self):
        try:
            return self.stack[-1]
        except IndexError:
            return None
    
    @profile
    def pop(self):
        top = self.top()
        top = top.toTuple()
        self.stack.pop()
    
    @profile
    def push(self, pos):
        if len(self.stack) >= bach.max_subdocument_depth:
            raise BachParseLimitError("maximum document nesting depth exceeded", 'max_subdocument_depth', pos)
        if self.numSubdocs >= bach.max_subdocuments_globally:
            raise BachParseLimitError("maximum global subdocument limit exceeded", 'max_subdocuments_globally', pos)
    
        d = Document()
        self.top().addSubdoc(d, pos)
        self.stack.append(d)
        self.numSubdocs += 1


@profile
def parse(stream, shorthandMapping={}):
    tokens = pairwise(tokenise(stream, shorthandMapping.keys()))
    
    state = ParserState()
    
    while True:
        try:
            current, lookahead = next(tokens)
        except StopIteration:
            break

        (tokenType, lexeme, pos) = current        
        if lookahead: lookahead = lookahead[0] # only need the type
        
        if tokenType is CaptureSemantic.label:
            state.setLabel(lexeme, pos)
        elif tokenType is CaptureSemantic.literal:
            state.addLiteral(lexeme, pos)
        elif tokenType is CaptureSemantic.subdocStart:
            state.push(pos)
        elif tokenType is CaptureSemantic.subdocEnd:
            state.pop()
        
        elif tokenType is CaptureSemantic.attribute:
            if lookahead is CaptureSemantic.assign:
                _, _ = next(tokens)
                current, _ = next(tokens)
                (tokenType, value, _) = current
                assert tokenType is CaptureSemantic.literal # enforced by grammar
                state.top().addAttribute(lexeme, pos, value=value)
            else:
                state.top().addAttribute(lexeme, pos)
        
        elif tokenType is CaptureSemantic.shorthandSymbol:
            assert lookahead is CaptureSemantic.shorthandAttrib # enforced by grammar
            current, _ = next(tokens)
            (_, value, _) = current
            attribName = shorthandMapping[lexeme] # enforced by grammar
            assert type(attribName) is str 
            state.top().addAttribute(attribName, pos, value=value)

        else:
            raise BachSemanticError("Unexpected %s" % tokenType, state, pos)

    return state.root().toTuple()


@profile
def lexerErrorHint(state):
    if state.contains(ProductionSymbol.S):
        return \
"Parsing failed before the start of a valid document could be found. A Bach \
document must start with a left-aligned label, optionally preceeded by \
empty lines or left-aligned #-style comments."

    if state.top() in [ProductionSymbol.LSQ, ProductionSymbol.LDQ, ProductionSymbol.LBQ]:
        return \
"Parsing failed while looking at a string literal, probably because of a missing closing quote."

    if state.top() in [ProductionSymbol.LSQESC, ProductionSymbol.LDQESC, ProductionSymbol.LBQESC]:
        return \
"Invalid escape sequence inside a string literal. Use backslash to escape the backslash character or the closing quote character only."

    if state.top() in [ProductionSymbol.LD, ProductionSymbol.ALD, ProductionSymbol.LSD, ProductionSymbol.ALSD]:
        return \
"Invalid attribute pair. Remember that the right hand side of an attribute pair must be a string literal."

    if state.top() is ProductionSymbol.SD:
        return \
"Parsing failed before the end of a subdocument, probably because of a missing closing parenthesis or an unexpected character."

    return "No extra help is available for this error state, sorry."



