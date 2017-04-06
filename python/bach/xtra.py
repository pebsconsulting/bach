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


def toElement(etreeClass, bachDocument, parent):
    label, attributes, values = bachDocument
    
    if parent is not None:
        e = etreeClass.SubElement(parent, label)
    else:
        e = etreeClass.Element(label)
    
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
            e2 = toElement(etreeClass, i, e)
            lastElement = e2
    
    return e


def toElementTree(etreeClass, bachDocument):
    """Convert a bach document into an Element Tree (e.g. from lxml import
    etree as etreeClass) for querying with XPath or a CSS selector engine such
    as cssselect."""
    return toElement(etreeClass, bachDocument, None)

