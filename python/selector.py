"""
Converts a Bach document into an Element Tree for querying using
XPath and CSSSelector

Usage:
    cat examples/ElementTree.bach | python3 python/examples/ElementTree.py
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
attrib_mapping = \
{
    '#': 'id',
    '.': 'class',
}

def mergeattributes(shorthand, longhand, mapping=attrib_mapping):
    # create a dict for all keys in longhand, shorthand
    a = {}

    for s in shorthand:
        a[attrib_mapping[s]] = shorthand[s]
    
    for l in longhand:
        if l in a:
            a[l].append(longhand[l])
        else:
            a[l] = longhand[l]
    
    return a
    


def mketree(tree, parent=None):
    # convert a bach document into Element Tree
    # This is mostly straight forward, except for the "shorthand-attributes"
    # which must be translated into full attributes.

    # this is a quick recursive implementation but we don't have to worry about
    # a stack overflow because bach has sanity settings that limit the
    # depth of any tree
    
    # A bach document is (label, shorthand attributes, attributes, values)
    label, shorthand, attributes, values = tree
    
    if parent is not None:
        e = etree.SubElement(parent, label)
    else:
        e = etree.Element(label)
    
    fullattrib = mergeattributes(shorthand, attributes)
    for k,v in fullattrib.items():
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

tree = bach.parse(fp)
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





