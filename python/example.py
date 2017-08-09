import bach
import io
import sys

# Example Usage:
#     $ echo "document" | python3 ./example.py
#     $ cat document | python3 ./example.py


# HTML-style shorthands
shorthands = [
    # HTML classes are an ordered set, because classes shouldn't repeat
    bach.Shorthand(".", "class", set),

    # HTML IDs don't have a collection type, because only one can appear
    bach.Shorthand("#", "id"),

    # As a contrived example, lets invent a shorthand for flags like
    # "$feature1 $feature2", where options can appear multiple times separated
    # by semicolons
    bach.Shorthand("$", "feature", list, '; '),
]

# Configure the parser to use these shorthands
parser = bach.Parser(shorthands)

#  Get stdin as a unicode stream
fp = io.TextIOWrapper(sys.stdin.buffer, encoding=sys.stdin.encoding)

# Parse the input stream
tree = parser.parse(fp)

# -- You can use a string too, e.g: parser.parse("document 'example'")


# The result is a tree of bach.Documents:

# document.label - str
# document.attributes - mapping of str to a list of str values (shorthand expanded)
# document.children - a mixed list of bach.Documents and str values

print(repr(tree))

# TODO document.toXML, .toETree, etc.


