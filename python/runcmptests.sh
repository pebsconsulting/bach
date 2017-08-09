#!/bin/bash

PY="python3"

set -e

function testvalid {
    in="testdata/valid/$1.input.bach"
    out="testdata/valid/$1.expected.py"
    echo "TEST $in => $out"
    cat $in | $PY ./cmptest.py $out
}  


testvalid "0001"
