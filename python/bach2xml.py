"""
Parses a Bach document from stdin, with configurable shorthand attributes, and
prints the result to stdout as an XML document.

Example Usage:
    cat input.bach | python3 bach2xml.py > output.xml

Example configuring shorthand attribute expansion:
    cat input.bach | python3 bach2xml.py -s ".class" "#id" "?flag" > output.xml
    cat input.bach | python3 bach2xml.py --shorthand ".class" "#id" "?flag" > output.xml

E.g.
    echo "document .className" | python3 bach2xml.py -s ".class"
    >>>> <?xml version='1.0' encoding='utf-8'?>
    >>>> <document class="className"/>

Example configuring input and output encodings (either are optional; defaults to utf-8)
    cat input.bach | python3 bach2xml.py -i "Latin-1" -o "utf-8" > output.xml
    cat input.bach | python3 bach2xml.py --input-encoding "Latin-1" --output-encoding "utf-8" > output.xml
"""

import argparse
import bach
import io
import sys
from lxml import etree as ET



ap = argparse.ArgumentParser(
    description='Takes a bach document from stdin and writes an XML document to stdout')
ap.add_argument('-i', '--input-encoding',  default='utf-8',
    help='specify the input character encoding (defaults to utf-8)')
ap.add_argument('-o', '--output-encoding',  default='utf-8',
    help='specify the output character encoding (defaults to utf-8, must be utf-8 or utf-16)')
ap.add_argument('-s', '--shorthand', nargs="+", default=[],
    help='add shorthand attribute mappings e.g. --shorthand ".class" "#id" "?flag"')

args = ap.parse_args()
assert args.output_encoding.upper() in ['UTF-8', 'UTF-16']

shorthand = {}

for i in args.shorthand:
    assert len(i) >= 2, "Shorthand attribute mapping option must contain at least one symbol and at least one character"
    symbol, expansion = i[0], i[1:] 
    assert not symbol in shorthand, "Shorthand attribute symbol already configured"
    shorthand[symbol] = expansion

# Configure a parser using these shorthands
parser = bach.Parser(shorthand)

# Get the standard input binary buffer and wrap it in a file-object so that it
# decodes into a stream of Unicode characters from the specified encoding.
fp = io.TextIOWrapper(sys.stdin.buffer, encoding=args.input_encoding)

document = parser.parse(fp)
tree = document.toElementTree(ET)
xml = ET.tostring(tree, encoding=args.output_encoding, pretty_print=True, xml_declaration=True)

sys.stdout.buffer.write(xml)


