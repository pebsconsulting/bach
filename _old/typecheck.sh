#!/bin/bash

set -e

tc="mypy --python-version 3.4"

function require {
    command -v "$1" >/dev/null 2>&1 || { echo >&2 "Required: $1. Try something like: $2"; exit 1; }
}

require mypy "sudo pip3 install -U typing mypy"

echo "Typechecking..."
echo "    Note that there are some false positives caused by incomplete type"
echo "    information for external modules. Help fix this by contributing to"
echo "    Typeshed: https://github.com/python/typeshed"
$tc python

