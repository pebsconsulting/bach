#!/bin/bash

set -e

function require {
    command -v "$1" >/dev/null 2>&1 || { echo >&2 "Required: $1. Try something like: $2"; exit 1; }
}

require pylint2 "sudo pip3 install astroid isort pylint"

for i in `find . -type f -name "*.py" | xargs`
do
    echo "$i"
    pylint -E "$i"
done
