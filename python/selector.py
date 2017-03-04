"""
Converts a Bach document into an Element Tree for querying using
XPath and CSSSelector

Usage:
    cat examples/selector.bach | python3 python/selector.py
Dependencies:
    sudo apt-get install libxml2-dev libxslt1-dev
    sudo pip3 install lxml
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
from lxml import etree


# mapping from shorthand attribute to longhand attribute
shorthandMapping = \
{
    '#': 'id',
    '.': 'class',
}
  


def mketree(tree, parent=None):
    # convert a bach document into Element Tree
    
    # A bach document is (label, attributes, values)
    label, attributes, values = tree
    
    if parent is not None:
        e = etree.SubElement(parent, label)
    else:
        e = etree.Element(label)
    
    for k,v in attributes.items():
        e.set(k, ' '.join(v))

    lastElement = e
    for i in values:
        if type(i) is str:
            if lastElement == e:
                lastElement.text = i
            else:
                lastElement.tail = i
        else:
            e2 = mketree(i.toTuple(), parent=e)
            lastElement = e2
    
    return e



ap = argparse.ArgumentParser()
ap.add_argument('-e', '--encoding',  default='utf-8',
    help='specify the input character encoding (defaults to utf-8)')

args = ap.parse_args()

fp = io.TextIOWrapper(sys.stdin.buffer, encoding=args.encoding, newline='')

tree = bach.parse(fp, shorthandMapping)
root = mketree(tree)

print("Converted into an ElementTree")
print(etree.tostring(root))

print("Now running XPATH query: //span")
find = etree.XPath("//span")
for i in find(root):
    print("    Text of result is: %s" % repr(i.text))

print("Now running cssselect for span.fancy")
find = GenericTranslator().css_to_xpath('span.fancy')
print("This translates into %s" % repr(find))
find = etree.XPath(find)
for i in find(root):
    print("    Text of result is: %s" % repr(i.text))





