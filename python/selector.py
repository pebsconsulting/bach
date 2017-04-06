"""
Example - converts a Bach document into an Element Tree
for querying using XPath and CSSSelector.

Usage:
    cat examples/selector.bach | python3 python/selector.py
Dependencies:
    sudo apt-get install libxml2-dev libxslt1-dev zlib1g-dev
    sudo pip3 install cssselect lxml
Read:
    http://lxml.de/api.html
    http://effbot.org/zone/element-index.htm
    http://lxml.de/xpathxslt.html#the-xpath-method
    http://lxml.de/cssselect.html
"""

import argparse
import io
import sys
import bach

from cssselect import GenericTranslator
from lxml import etree as ET # or the equivalent ElementTree class from another module


ap = argparse.ArgumentParser()
ap.add_argument('-e', '--encoding',  default='utf-8',
    help='specify the input character encoding (defaults to utf-8)')

args = ap.parse_args()

fp = io.TextIOWrapper(sys.stdin.buffer, encoding=args.encoding, newline='')

# mapping from shorthand attribute to longhand attribute
shorthandMapping = \
{
    '#': 'id',
    '.': 'class',
}

tree = bach.parse(fp, shorthandMapping)

# convert to an ElementTree
rootElement = bach.toElementTree(ET, tree)

print("Converted into an ElementTree")
print(ET.tostring(rootElement))

print("Now running XPATH query: //span")
find = ET.XPath("//span")
for i in find(rootElement):
    print("    Text of result is: %s" % repr(i.text))

print("Now running cssselect for span.fancy")
find = GenericTranslator().css_to_xpath('span.fancy')
print("This translates into %s" % repr(find))
find = ET.XPath(find)
for i in find(rootElement):
    print("    Text of result is: %s" % repr(i.text))





