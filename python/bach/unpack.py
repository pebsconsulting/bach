import binascii



class CompiledGrammar():
    """This is a compiled representation of a Deterministic Pushdown Automaton
    (DPDA) for a formal grammar representing the Bach language.

    See grammar.txt for the source and cgrammar.py for the compiler."""
    
    # Special fixed IDs for terminal sets
    TERMINAL_SET_NONE_ID = 0 # empty set
    TERMINAL_SET_EOF_ID  = 1 # end of file
    TERMINAL_SET_SS_ID   = 2 # runtime shorthand separators
    TERMINAL_SET_DSS_ID  = 3 # disallowed shorthand separators
    TERMINAL_SET_SC_ID   = 8 # special characters

    packed = """
626163682d6367311614233d20090d0a282922275b5d3c3e5c275c5b5c2215000000001414010f02
0502060e0f05060014080b01020001070806070809090a0a0b0b0c12140e1010120007070209030c
010d020f0312031503180119011a011b0c27042b012c022e04320c3e044201430245024701040300
ff07000401030087000700ffff80000b04030087000b0300ff070088020bff05e1880e0bff88c104
ffffff84000401ffff040005ffffff850005ffffff01000502ffff050007ffffff800087ffffff07
008704ffff87000fffffff80209305ffff8080060805ff80000effffff80209206ffff8080060906
ff800011ffffff80209407ffff8080060a07ff800013ffffff808012ffffff808014ffffff808005
0bffff850005ffffff010005020bff050002130bff88e788020bff05e2880e0bff88c2880dffff0a
e20a0cffff80e40d0f0bff80e50e060bff80430f050bff804310070bff8043050cffff80000e060b
ff80430f050bff804310070bff80430a0cffff80e488ffffff08a0880effff8880050fffff800088
0210ff05e1880e10ff88c18810ffff0ce1021410ff88e7880210ff05e2880e10ff88c28810ffff0c
e28812ffff0ae20a11ffff80e40d0f10ff80e50cffffff80e60510ffff80000e0610ff80430f0510
ff8043100710ff80430511ffff80000e0610ff80430f0510ff8043100710ff80430a11ffff80e488
ffffff08e8880effff88c888ffffff08e8880effff88c80cffffff8000010b55
"""

    def __init__(self):
        self.data = binascii.unhexlify("".join(self.packed.split()))
        self.verify()
        self.parse()


    def verify(self):

        # verify header
        header = self.data[0:8]
        assert header == b"bach-cg1"

        # verify checksum
        checksum = self.data[-1]
        assert (sum(self.data) - checksum) % 255 == checksum


    def readPascalString(self, index):
        # From index, read the length (one byte) then the string of that length
        # Return (new index, value)
        length = self.data[index]
        value = self.data[index+1:index+length+1]
        return index + length + 1, value


    def allowableShorthandSymbol(self, symbol):
        # symbol allowed by grammar for shorthand syntax?
        # read disallowed from TERMINAL_SET_DSS_ID
        index = self.offsetToTerminalSets + (2 * self.TERMINAL_SET_DSS_ID)
        start = self.data[index]
        end = self.data[index+1]
        disallowed = self.terminalString[start:end]
        return symbol not in disallowed


    def terminalSets(self, shorthandSeparators):
        # extracts a list of strings, ordered by terminal set ID,
        # from the compiled representation

        index = self.offsetToTerminalSets
        for i in range(0, self.numTerminalSets):
            if i == self.TERMINAL_SET_SS_ID:
                # patch the (empty) shorthand separators set
                # with the runtime-configured symbols
                yield shorthandSeparators
            else:
                start = self.data[index]
                end   = self.data[index+1]
                result = self.terminalString[start:end]
                if i == self.TERMINAL_SET_SC_ID:
                    result = ''.join(set(result + shorthandSeparators))
                yield result
            index += 2


    def stateProductions(self, i, ProductionType):
        # extracts a list of production rules for a given state
        # from the compiled representation
        # (order should not matter - productions are deterministic!)

        index = self.offsetToRules + (self.stateIndexes[i] * self.ruleBytes)
        numProductions = numProductions = self.stateNumRules[i]

        for i in range (0, numProductions):
            yield CompiledProduction.unpack(self.data[index:index+self.ruleBytes], ProductionType)
            index += self.ruleBytes


    def states(self, ProductionType):
        # extracts a list, ordered by state ID, of production rules
        # from the compiled representation

        index = self.offsetToRules
        for i in range(0, self.numStates):
            yield list(self.stateProductions(i, ProductionType))


    def terminals(self):
        # The set of (N.B. differs from self.terminalString, which may contain
        # duplicates or a different ordering!), for quick membership tests
        return ''.join(self.terminalString)


    def parse(self):
        # read the initial structure/offsets/etc of the compiled representation
        data = self.data

        self.numStates = data[8]
        index, terminalString = self.readPascalString(9)
        self.terminalString = terminalString.decode('utf-8')

        self.numTerminalSets = data[index]
        index += 1

        # block of default terminal set start,end pairs
        self.offsetToTerminalSets = index
        index += 2 * self.numTerminalSets

        # block of state rule indexes and rules-per-state
        self.stateNumRules = [0] * self.numStates
        self.stateIndexes  = [0] * self.numStates

        totalRules = 0
        for i in range(0, self.numStates):
            self.stateIndexes[i]  = data[index]
            self.stateNumRules[i] = data[index+1]
            totalRules += self.stateNumRules[i]
            index += 2

        # block of rules
        self.offsetToRules = index
        self.ruleBytes     = 6

        # end states list
        index = self.offsetToRules + (self.ruleBytes * totalRules) 
        numEndStates = data[index]
        self.endStates = [x for x in data[index+1:index+1+numEndStates]]



class CompiledProduction():
    """This class represents a compiled representation of a production rule
    in a CompiledGrammar"""

    @staticmethod
    def unpack(data, ProductionType):
        assert len(data) == 6
        return ProductionType(
            CompiledProduction.invget(data[0]),
            CompiledProduction.invget(data[4]),
            list(CompiledProduction.ids(data[1:4])),
            CompiledProduction.capget(data[5]))

    @staticmethod
    def ids(xs):
        for i in xs:
            if i != 255:
                yield i

    @staticmethod
    def invget(value):
        if (0b10000000 & value) == 0b10000000:
            return value & 0b01111111, True
        else:
            return value, False

    @staticmethod
    def capget(x):
        c, cstart, cend, cas = False, False, False, 0
        
        if (x & 0b10000000) == 0b10000000: c = True
        if (x & 0b01000000) == 0b01000000: cstart = True
        if (x & 0b00100000) == 0b00100000: cend = True
        
        cas = x & 0b00011111

        return c, cstart, cend, cas


