import bach
import io
import sys

# Example Usage:
#     $ echo "document" | python3 ./example.py
#     $ cat document | python3 ./example.py


# Lets extend our language with some HTML-style shorthands
# this lets us write ".someClass #someId" in our bach document
shorthands = {'.': 'class', '#': 'id'}

# Configure a parser using these shorthands
parser = bach.Parser(shorthands)

#  Get stdin as a unicode stream
fp = io.TextIOWrapper(sys.stdin.buffer, encoding=sys.stdin.encoding)

# Parse the input stream
document = parser.parse(fp)

# -- You can use a string too, e.g: parser.parse("document 'example'")


# The result is a tree of bach.Documents:

# document.label - str
# document.attributes - mapping of str attribute names to str attribute values;
#                       shorthand attributes are expanded to their full names
# document.children - a mixed list of bach.Documents and/or str values

print("\nAs Python Literals:")
print(repr(document))



# We can convert it into an LXML ElementTree

from lxml import etree as ET

tree = document.toElementTree(ET)


# Which we can convert into XML...

xml = ET.tostring(tree, encoding=sys.stdin.encoding, pretty_print=True, xml_declaration=True).decode('utf-8')

print("\nAs XML:")
print(xml)



