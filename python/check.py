"""
Parses a Bach document from stdin - does nothing if there's no error
"""

import io
import sys
import bach

# Get the standard input binary buffer and wrap it in a file-object so that it
# decodes into a stream of Unicode characters from the specified encoding. We
# do this without Python translating any linebreaks (omit the newline argument
# if you like the default behaviour; the parser can cope with either).
fp = io.TextIOWrapper(sys.stdin.buffer, encoding=sys.stdin.encoding)

tree = bach.Parser().parse(fp)


