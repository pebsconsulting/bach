# Bach

**An XML-interoperable general-purpose semantic document markup language**

![bach logo](logo-640.png)


Bach is for anyone hand-authoring structured semantic text that is parsed into
a data structure to be transformed programmatically. It is fully interoperable
with your existing XML-based tooling, but it's a lot nicer to read and write!

Our key use cases for Bach are multilingual documents, technical
documentation, and static website generators.


## Key Features

### Convert to and from XML, Python Literals, Python XML Element Trees

Bach documents have a 1:1 mapping between XML; a recursive data structure made
up of native Python types and string literals; Python Element Trees, and more.
Use Bach with all the powerful tools you expect, like XLST, XQuery, DTD and
XML Schemas.

### Shorthand attribute syntax configurable at parse-time

A special "shorthand" syntax can expand attributes like `.myClass` into
`class="myClass"`. The shorthand syntax is fully configurable at parse-time,
including (soon) customisable encoding of lists and sets e.g. how to combine
multiple CSS classes into one attribute.

### Efficient portable parser

The language grammar is formally defined and compiled into a compact portable
representation, making it easy to parse Bach documents in your chosen language.

Bach documents are parseable in linear time to the length of the input and one
byte of lookahead i.e. with an LL(1) parser.

This repository contains reference implementations for both Python (>=3.4) and
(soon!) C.

## Examples

Here is a basic example without XML namespaces.

    document
    
    (person
        (name
            (forename       "Grace")
            (surname        "Hopper")
            (other-names    "Brewster Murray")
            (nicknames      (nickname "Amazing Grace"))
            (aliases)
        )
        (dob        "19061209")
        (bio
            "Grace Brewster Murray Hopper was an American "
            (wiki "computer scientist")
            " and United States Navy rear admiral."

            src="https://en.wikipedia.org/wiki/Grace_Hopper"
        )
    )

Here's an example with XML namespaces:

    # Example based on https://msdn.microsoft.com/en-us/library/aa468565.aspx

    document
        xmlns:d="http://www.develop.com/student"
    
        (d:student
            (d:id       "3235329")
            (d:name     "Jeff Smith")
            (d:language "Python")
            (d:rating   "9.5")
        )

# Syntax and Semantics

A Bach document is a non-empty string that may start with #-style comments,
followed by a label, then optionally attributes, shorthand attributes, string
literals, and subdocuments in any order. Subdocuments may not contain #-style
comments, but may contain #-style shorthand attributes instead.

Special characters are space, backslash, and

    #=\t\r\n()[]{}<>"'

Special characters used for shorthand attributes are given to the parser as a
mapping from shorthand symbols to attribute names.

A label is any string of non-special characters appearing as the first
thing in a document or subdocument.

A string literal is quoted by single, double, or bracket quotes. Closing quotes
may be escaped with backslash. A literal backlash must also be escaped.

    'a string'
    "a string"
    [a string]
    'a \' \\ string'
    "a \" \\ string"
    [a \] \\ string]

A shorthand attribute starts with a special shorthand character specified
earlier.

A shorthand attribute then is followed by any string of non-special characters.

    #anAttribute
    .anAttribute
    !anAttribute

This is quite similar to the syntax of CSS selectors. For example:

    (anElement#someId.classOne.classTwo enabled title="An Example Element")

Full attributes are any string of non-special characters followed by an equals
followed by a string literal. Whitespace is optional.

    anAttribute="a value"
    anAttribute = "a value"

The assignment may be ommitted, in which case the attribute is present but with
a value such as `Null` or `None` (as distrinct from the empty string).
***This behaviour may change for XML compatibility***

    (item anAttributeWithNoValue)

Subdocuments start and end with brackets. They are always non-empty.

    document (subdocument "a literal" (anotherSubdocument) "another literal")


## Open Standard

Tawesoft Ltd is committed to supporting Bach as an Open Standard. At this early
stage we invite feedback and comments but, if and as soon as the need arises,
we are keen to see democratic and inclusive stewardship of the language.

A full machine-readable formal grammar is given at [grammar.txt](grammar.txt).
The rules are given in Greibach Normal Form with additional lookahead and
semantic notation.


## Name

Bach is named for the Welsh term of endearment (literally "small") and as
tribute to the work of computer scientist
[Sheila Greibach](https://en.wikipedia.org/wiki/Sheila_Greibach).


## License

This license applies to the Bach Reference Implementation(s) and associated
documentation.

    Bach - XML-interoperable general-purpose semantic document markup language

    Copyright © 2017 Ben Golightly <ben@tawesoft.co.uk>
    Copyright © 2017 Tawesoft Ltd <opensource@tawesoft.co.uk>

    Permission is hereby granted, free of charge, to any person obtaining a copy
    of this software and associated documentation files (the "Software"), to deal
    in the Software without restriction,  including without limitation the rights
    to use,  copy, modify,  merge,  publish, distribute, sublicense,  and/or sell
    copies  of  the  Software,  and  to  permit persons  to whom  the Software is
    furnished to do so, subject to the following conditions:

    The above copyright notice  and this permission notice  shall be  included in
    all copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED  "AS IS",  WITHOUT WARRANTY OF ANY KIND,  EXPRESS OR
    IMPLIED,  INCLUDING  BUT  NOT LIMITED TO THE WARRANTIES  OF  MERCHANTABILITY,
    FITNESS FOR A PARTICULAR PURPOSE  AND NONINFRINGEMENT.  IN NO EVENT SHALL THE
    AUTHORS  OR COPYRIGHT HOLDERS  BE LIABLE  FOR ANY  CLAIM,  DAMAGES  OR  OTHER
    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
    SOFTWARE.

