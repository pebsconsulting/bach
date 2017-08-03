# https://github.com/tawesoft/bach/issues/2

import bach
import io
import sys

# OK:
# document = bach.parse(io.StringIO('point xx="1" yy="2" zz="3"\n'))

# Was failing:
document = bach.parse(io.StringIO('point x="1" y="2" z="3"\n'))

label, attributes, subdocuments = document
assert label == "point"
assert len(attributes) == 3
assert attributes['x'] == ["1"]
assert attributes['y'] == ["2"]
assert attributes['z'] == ["3"]
assert len(subdocuments) == 0

