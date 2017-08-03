# Compile grammar to a portable and efficient binary representation

# Usage: cat grammar.txt | python3 ./cgrammar.py > compiled-grammar.txt

import sys
import binascii

HEADER = 'bach-cg1' # [8] Bach compiled grammar format 1


class IDMapper():
    def __init__(self):
        self.ids = {}

    def add(self, name, id=None):
        assert name not in self.ids
        if id is None: id = len(self.ids)
        self.ids[name] = id
        return self.ids[name]

    def idof(self, name):
        try:
            return self.ids[name]
        except IndexError:
            return self.add(name)
    
    def entries(self):
        return len(self.ids)


class TerminalSet():
    def __init__(self, start, end):
        self.start = start
        self.end   = end


class TerminalSets():
    def __init__(self):
        self.ids = {}

    def add(self, name, id=None, data=None):
        assert name not in self.ids
        if id is None: id = len(self.ids)
        self.ids[name] = (id, data)
        return self.ids[name]

    def get(self, name):
        return self.ids[name]
    
    def entries(self):
        return len(self.ids)


class ProductionRule():
    def __init__(self, terminalSetId, invertTerminalSet, nonterminalIds,
            lookaheadTerminalId, invertLookaheadTerminal,
            capture, captureStart, captureEnd, captureAs):
        assert len(nonterminalIds) <= 3
        self.terminalSetId  = terminalSetId # non-terminal produced by rule
        self.invertTerminalSet = invertTerminalSet
        self.nonterminalIds = nonterminalIds # zero or more (max 3) non-terminals
        self.lookaheadTerminalId = lookaheadTerminalId
        self.invertLookaheadTerminal = invertLookaheadTerminal
        self.capture = capture
        self.captureStart = captureStart
        self.captureEnd = captureEnd
        self.captureAs = captureAs
        # upper three bits: capture, capture start, capture end
        # lower five (four) bits:  capture semantic
        # Set high bit of ID to invert e.g. NOT an element of set

    def pack(self):
        def inv(value, inverter):
            assert value <= 127
            if inverter:
                return 0b10000000 | value
            else:
                return value
    
        b = []
        b.append(inv(self.terminalSetId, self.invertTerminalSet))
        b.extend(self.nonterminalIds)
        if len(self.nonterminalIds) < 3:
            b.extend([255] * (3 - len(self.nonterminalIds)))
            # ID 255 marks end of rule

        b.append(inv(self.lookaheadTerminalId, self.invertLookaheadTerminal))
        
        c = 0
        if self.capture:
            c |= 0b10000000
        if self.captureStart:
            c |= 0b01000000
        if self.captureEnd:
            c |= 0b00100000
        
        assert self.captureAs <= 16
        c |= self.captureAs
        
        b.append(c)
        
        return b


class ProductionRules():
    def __init__(self):
        self.rules = {}
    def add(self, nonterminalSymbolId, rule):
        try:
            self.rules[nonterminalSymbolId].append(rule)
        except KeyError:
            self.rules[nonterminalSymbolId] = [rule]
        return rule
    def get(self, id):
        try:
            return self.rules[id]
        except KeyError:
            return []
    def states(self):
        return len(self.rules)
    def totalRules(self):
        total = 0
        for i in self.rules:
            total += len(self.rules[i])
        return total

def intify(x):
    try:
        return int(x)
    except ValueError:
        return 10 + ord(x) - ord('A')


def tokenparse(clause):
    inQuote=False
    escape=False
    result = []
    
    for c in clause:
        if (escape):
            escape=False
        else:
            if c == '\\':
                escape = True
            elif c == '"':
                inQuote = not inQuote
            elif c == ' ':
                if not inQuote:
                    if result: yield result
                    result = []
                    continue
        
        result.append(c)
    
    if result: yield result


def clauseparse(line):
    inQuote=False
    escape=False
    result = []
    
    for c in line:
        if (escape):
            escape=False
        else:
            if c == '\\':
                escape = True
            elif c == '"':
                inQuote = not inQuote
            elif c == ';':
                if not inQuote:
                    yield result
                    result = []
                    continue
            elif c == '#':
                if not inQuote:
                    yield result
                    result = []
                    return
        
        result.append(c)
    
    if result: yield result
        

def lineparse(line):
    results = []
    clauses = [''.join(x).strip() for x in clauseparse(line)]
    for clause in clauses:
        tokens = [''.join(x).strip() for x in tokenparse(clause)]
        results.append(tokens.copy())
    return results


def unquote(s):
    result = []
    escape = False
    inQuote = False
    
    for c in s:
        if escape:
            escape = False
            if c == 'n':
                result.append('\n')
            elif c == 'r':
                result.append('\r')
            elif c == 't':
                result.append('\t')
            else:
                result.append(c)
        elif inQuote:
            if c == "\\":
                escape = True
            elif c == "\"":
                inQuote = False
            else:
                result.append(c)
        else:
            if c == "\"":
                inQuote=True
            else:
                raise SyntaxError
    
    return ''.join(result)
    


productionSymbolMapper = IDMapper()
captureSemanticMapper  = IDMapper()
terminalSetMapper      = TerminalSets()
productionRules        = ProductionRules()


print("# Lines beginning with # are for human debugging information only")
rules = 0
for line in sys.stdin:
    line = line.strip()
    if not len(line): continue
    if line[0] == '#': continue
    
    if line[0] == '[':
        mode = line[1:-1]
        print("# Section: [%s]" % mode)
        continue
    
    if mode == 'Production Symbols':
        name = lineparse(line)[0][0] # clause 0, part 0
        id = productionSymbolMapper.add(name)
        print("#    %s %d" % (name, id))
        
    elif mode == 'Capture Semantics':
        name, id = lineparse(line)[0] # clause 0, tokens 0 and 1
        print("#    %s %s" % (name, id))
        captureSemanticMapper.add(name, int(id))
    
    elif mode == 'Terminals':
        terminals = unquote(lineparse(line)[0][0]) # clause 0, part 0
        print("#    (%d): %s" % (len(terminals), ', '.join([str(ord(x)) for x in terminals])))
    
    elif mode == 'Terminal Sets':
        name, id, start, end = lineparse(line)[0] # clause 0, tokens 0 to 3
        id, start, end = intify(id), intify(start), intify(end)
        print("#    %s: %d %d-%d" % (name, id, start, end))
        terminalSetMapper.add(name, id, TerminalSet(start, end))
    
    elif mode == 'Production Rules':
        p = lineparse(line)
        rule = p[0]
        clauses = p[1:]
        
        productionSymbol = rule[0]
        assert rule[1] == '=>'
        terminalProduction = rule[2]
        nonterminalProductions = rule[3:]
        
        invertTerminalProductionSet = False

        lookaheadTerminal = 'special:none'
        invertLookaheadSet = True # Not None => All (any)
        
        capture = False
        captureStart = False
        captureEnd = False
        captureAs = 'none'
        
        if terminalProduction[0] == '¬':
            terminalProduction = terminalProduction[1:]
            invertTerminalProductionSet = True
        
        for clause in clauses:
            if clause[0] == 'lookahead':
                if clause[1] == 'not' and clause[2] == 'in':
                    invertLookaheadSet = True
                    lookaheadTerminal = clause[3]
                elif clause[1] == 'in':
                    invertLookaheadSet = False
                    lookaheadTerminal = clause[2]
                else:
                    raise SyntaxError
            elif clause[0] == 'C':
                capture = True
            elif clause[0] == 'CS':
                captureStart = True
            elif clause[0] == 'CE':
                captureEnd = True
            elif clause[0] == 'as':
                captureAs = clause[1]
            else:
                raise SyntaxError(clause)
        
        inv = "¬" if invertTerminalProductionSet else ''
        print("#    %s => %s%s %s" % (productionSymbol, inv, terminalProduction, \
            ' '.join(nonterminalProductions)))
        print("#        (%d => %s%s, [%s])" % (\
            productionSymbolMapper.idof(productionSymbol),
            inv,
            terminalSetMapper.get(terminalProduction)[0],
            ' '.join([str(productionSymbolMapper.idof(x)) for x in nonterminalProductions])))
        
        inv = "not in" if invertLookaheadSet else 'in'
        print("#        if lookahead %s %s (%d)" % (inv, lookaheadTerminal,
            terminalSetMapper.get(lookaheadTerminal)[0]))
        
        print("#        %s%s%s as %s (%d)" % (
            '[capture]' if capture else '',
            '[capture start]' if captureStart else '',
            '[capture end]' if captureEnd else '',
            captureAs,
            captureSemanticMapper.idof(captureAs)
        ))
        
        ruleId = productionSymbolMapper.idof(productionSymbol)
        rule = ProductionRule(
            terminalSetMapper.get(terminalProduction)[0],
            invertTerminalProductionSet,
            [productionSymbolMapper.idof(x) for x in nonterminalProductions],
            terminalSetMapper.get(lookaheadTerminal)[0],
            invertLookaheadSet,
            capture, captureStart, captureEnd,
            captureSemanticMapper.idof(captureAs))
        rules+=1
        productionRules.add(ruleId, rule)
    elif mode == 'END':
        break
    else:
        raise SyntaxError

print("# State Transitions")
assert productionRules.totalRules() == rules

numRulesForState = {}
offsetForState = {}
offset = 0

for i in range(0, productionSymbolMapper.entries()):
    numRulesForState[i] = len(productionRules.get(i))
    offsetForState[i] = offset
    print("#    state %d has %d rules starting at offset %d" % (i, numRulesForState[i], offsetForState[i]))
    offset += numRulesForState[i]



print("# Summary:")
print("#    HEADER: %s" % HEADER)
print("#    %d Parser States / %d Production Symbols" % \
    (productionRules.states(), productionSymbolMapper.entries()))
print("#    %d State Transitions / Rules" % rules)
print("#    %d sets of terminal characters defined by a mapping into %d chars" \
    % (terminalSetMapper.entries(), len(terminals)))

print("# Compiling...")
b = []

# First 8 bytes: header
b[0:8] = [ord(x) for x in HEADER]

# Number of states
states = productionSymbolMapper.entries()
assert states <= 127
b.append(states)

# Terminal String
assert len(terminals) < 127
b.append(len(terminals))
b.extend(terminals.encode('latin1'))

# Terminal Sets
sets = terminalSetMapper.entries()
assert sets < 127
b.append(sets)

# Terminal Sets index into string
for i in sorted(terminalSetMapper.ids, key=lambda x: terminalSetMapper.get(x)[0]):
    item = terminalSetMapper.get(i)[1]
    start = item.start
    end = item.end
    assert start < 127
    assert end < 127
    b.append(start)
    b.append(end)

# Number of rules and offset for each state
for i in range(0, states):
    o = offsetForState[i]
    n = numRulesForState[i]
    assert o <= 127
    assert n <= 127
    b.append(o)
    b.append(n)

# Rules
for i in range(0, states):
    for j in range(0, numRulesForState[i]):
        b.extend(productionRules.get(i)[j].pack())

checksum = 0
for i in b:
    checksum += i
    checksum %= 255

b.append(checksum)

print("#    State machine compiled to %d bytes" % len(b))
print("#    Checksum: %d" % checksum)
print("# HEX output follows.")

def chop(str, num):
    # https://stackoverflow.com/a/5711460/275677
    return [str[start:start+num] for start in range(0, len(str), num)]

print('\n'.join(chop(binascii.hexlify(bytes(b)).decode('us-ascii'), 80)))


