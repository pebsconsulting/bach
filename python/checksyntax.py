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

import argparse
import io
import sys
import bach

ap = argparse.ArgumentParser(
    description='Check the syntax of a Bach document from standard input')
ap.add_argument('-e', '--encoding',  default='utf-8',
    help='specify the input character encoding (defaults to utf-8)')

args = ap.parse_args()

# Get the standard input binary buffer and wrap it so it decodes into a
# stream of Unicode characters from the specified encoding. We do this without
# Python translating any linebreaks (omit the newline argument if you like the
# default behaviour; the parser can cope with either).
fp = io.TextIOWrapper(sys.stdin.buffer, encoding=args.encoding, newline='')

# We now have a file-object (https://docs.python.org/3.4/glossary.html#term-file-object)
# that can be read a valid Unicode character at a time.
bach.parse(fp)


