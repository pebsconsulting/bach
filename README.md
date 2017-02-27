# Bach

**A general-purpose semantic document markup language**

This repository contains the reference implementation for Python >= 3.4

![bach logo](logo-640.png)


## At-A-Glance

A Bach document is a tuple:

    document = (label, shorthand-attributes, attributes, contents)

The *label* is a string with has domain-specific semantics. You might like to think of it as a function name.

The *shorthand-attributes* is a mapping of special shorthand symbol characters to an array of attribute value strings.

The *attributes* is a mapping of attribute name strings to attribute value strings.

The *contents* is an ordered collection of zero or more string literals and/or Bach documents recursively.

Documents written in the Bach markup language are efficiently parsed into this structure with an LL(1) parser.

Once in this structure, Bach documents can be easily manipulated using code.


## Example

How best to structure a document depends on your application domain. Here is one example.

    document
    
    (metadata
        (copyright
            author="Wikipedia Contributors"
            source="https://en.wikipedia.org/wiki/Aardvark"
            license="https://creativecommons.org/licenses/by-sa/3.0/"
        )
        (tags
            "animal"
            "nocturnal"
            "Africa"
        )
    )
    
    (h1 "Aardvark")
    
    (p
        "The aardvark is a medium-sized, burrowing, nocturnal"
        (a "mammal" href="https://en.wikipedia.org/wiki/Mammal")
        "native to Africa."
        (cite #NEB10 location="pp. 3-4")
    )
    
    
    (citations
        (book #NEB10
            chapter     = "Aadvark"
            author      = "Hoiberg, Dale H., ed."
            title       = "The New Encyclopædia Britannica: Macropaedia, Knowledge in depth"
            edition     = "15"
            publisher   = "Encyclopædia Britannica"
            pubdate     = "2010"
        )
    )


# Syntax and Semantics

A Bach document is a non-empty string that may start with #-style comments, followed by a label, then optionally attributes, string literals, and subdocuments in any order. Subdocuments may not contain #-style comments.

Special characters are

    #.*^?!@|~$=:\t\r\n ()[]{}<>"'\\/

A label is any string of non-special characters.

A string literal is quoted by single, double, or bracket quotes. Closing quotes may be escaped with backslash. A literal backlash must also be escaped.

    'a string'
    "a string"
    [a string]
    'a \' \\ string'
    "a \" \\ string"
    [a \] \\ string]

A shorthand attribute starts with a special shorthand seperator:

    #.*^?!@|~$

A shorthand attribute then is followed by any string of non-special characters.

    #anAttribute
    .anAttribute
    !anAttribute

This is quite similar to the syntax of CSS selectors. For example:

    (anElement#someId.classOne.classTwo enabled title="An Example Element")

Full attributes are any string of non-special characters followed by an equals or colon followed by a string literal. Whitespace is optional.

    anAttribute="a value"
    anAttribute: "a value"
    anAttribute = "a value"

The assignment may be ommitted, in which case the attribute is present but with a value such as `Null` or `None` (as distrinct from the empty string).

    (item anAttributeWithNoValue)

Subdocuments start and end with brackets. They are always non-empty.

    (document "a literal" (subdocument) "another literal")

No duplicate full attributes are permitted in any (sub)document.

No duplicate shorthand attributes with the same symbol are permitted in any (sub)document.


## Open Standard

A full formal grammar, given in Greibach Normal Form with lookahead and semantic notation, is given in the source code.

This is the Python reference implementation of Bach. While efficient by the standards of a pure-Python parser, it is hoped that faster implementations, probably written at least partly in C, will become available.

Tawesoft Ltd is committed to supporting Bach as an Open Standard. At this early stage we invite feedback and comments but, if and as soon as the need arises, we are keen to see democratic and inclusive stewardship of the language.


## License

    Bach - a general-purpose semantic document markup language
    
    Python Reference Implementation

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
