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

# If True, syntax errors also print out the lexer state stack
debug=False

# If True, enables the @profile decorator from builtins.profile
# for use with profiling tools e.g. kernprof
profile=False

# Internal buffer size - 64k gives good performance
bufsz=64*1024

# Sanity settings to avoid malicious inputs
# -- parse speed is always linear to the input size,
# -- but memory consumption isn't
# -- string lengths are characters, not bytes

max_label_name_len          =           127
max_attribute_name_len      =           127

max_attribute_value_len     =      256*1024
max_literal_value_len       =   4*1024*1024
max_lexeme_len              =   4*1024*1024

max_attributes_per_subdoc   =          1024
max_subdocuments_per_subdoc =       32*1024
max_literals_per_subdoc     =       32*1024

max_subdocument_depth       =            64

max_subdocuments_globally   =      256*1024
max_literals_globally       =      256*1024


from .parse import parse, BachError

