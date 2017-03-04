"""
Parses a Bach document and prints the result as a Python object

Usage:
    cat examples/simple.bach | python3 python/checksyntax.py
    cat examples/shorthand.bach | python3 python/checksyntax.py -s "#id" ".class"
"""

import argparse
import io
import sys
import bach

ap = argparse.ArgumentParser(
    description='Check the syntax of a Bach document from standard input')
ap.add_argument('-e', '--encoding',  default='utf-8',
    help='specify the input character encoding (defaults to utf-8)')
ap.add_argument('-s', '--shorthand', nargs='*', default=[],
    help='add a Shorthand argument (e.g. -s "#id" ".class")')

args = ap.parse_args()

# Get the standard input binary buffer and wrap it in a file-object so that it
# decodes into a stream of Unicode characters from the specified encoding. We
# do this without Python translating any linebreaks (omit the newline argument
# if you like the default behaviour; the parser can cope with either).
fp = io.TextIOWrapper(sys.stdin.buffer, encoding=args.encoding, newline='')

shorthandMapping = {}

# Convert the commandline arguments into a dict {shorthand: longhand}
for i in args.shorthand:
    assert len(i) >= 2
    left = i[0]
    right = i[1:]
    shorthandMapping[left] = right

tree = bach.parse(fp, shorthandMapping)
print(repr(tree))

