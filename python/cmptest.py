import ast
import bach
import io
import sys

# Example Usage, where input-document is a bach document and
# expected-document is a Python AST

#     $ cat input-document | python3 ./cmptest.py expected-document


def cmp(a, b):
    if type(a) is str:
        assert type(b) is str
        assert a == b
        return True

    labelA, attributesA, childrenA = a.label, a.attributes, a.children
    labelB, attributesB, childrenB = b

    assert labelA == labelB
    
    for a in attributesA:
        assert a in attributesB
        assert attributesA[a] == attributesB[a]
    for b in attributesB:
        assert b in attributesA
    
    assert len(childrenA) == len(childrenB)
    it = iter(childrenB)
    for a in childrenA:
        b = next(it)
        assert cmp(a, b)

    return True
    





parser = bach.Parser()

#  Get stdin as a unicode stream
fp = io.TextIOWrapper(sys.stdin.buffer, encoding=sys.stdin.encoding)

# Parse the input stream
tree = parser.parse(fp)

with open(sys.argv[1], 'r') as f:
    expected = ast.parse(f.read(), mode='eval')
    expected = eval(compile(expected, '', 'eval'))


cmp(tree, expected)


