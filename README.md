# Bach

**An XML-interoperable general-purpose semantic document markup language**

![bach logo](logo-640.png)


Bach is for anyone hand-authoring structured semantic text that is parsed into
a data structure to be transformed programmatically. It is fully interoperable
with your existing XML-based tooling, but it's a lot nicer to read and write!

This repository contains the language definition, a pure Python (3.4) parser
as a reference implementation, a C parser (soon!) and test suite (soon!).


## Key Features


### Convert to and from XML and native language types

Use Bach with all the powerful tools you expect, like XLST, XQuery, DTD and
XML Schemas.

Bach documents have a 1:1 mapping between several formats including XML, XHTML,
Python literals, Python LXML Element Trees, "the subset of Lisp data where the
first item in a list is required to be atomic", and more.


### Shorthand attribute syntax configurable at parse-time

A special "shorthand" syntax can expand attributes like `.myClass` into
`class="myClass"`. The shorthand syntax is fully configurable at parse-time,
including customisable encoding of lists and sets e.g. how to combine
multiple CSS classes into one attribute.


### Efficient portable parser

Bach documents are parseable in linear time to the length of the input and one
byte of lookahead i.e. with an LL(1) parser.

The language grammar is formally defined in a machine-readable document,
then compiled into a compact portable representation. This makes it simpler
and quicker to write a Bach parser in your chosen language.


## Examples

Here is a basic example without XML namespaces.

    people
        author="Anne Editor"
    
    (person
        (name
            (forename       "Grace")
            (surname        "Hopper")
            (other-names    "Brewster Murray")
            (nicknames      (nickname "Amazing Grace"))
            (aliases)
        )
        (dob        "19061209")
        (summary
            "Grace Brewster Murray Hopper was an American"
            (wiki "computer scientist")
            "and United States Navy rear admiral."

            src="https://en.wikipedia.org/wiki/Grace_Hopper"
        )
    )


Here's an example with XML namespaces:

    # Example based on https://msdn.microsoft.com/en-us/library/aa468565.aspx

    d:student
        xmlns:d="https://www.example.org/student"
        xmlns:p='https://www.example.org/programming-language'
    
    (d:id        "3235329")
    (d:name      "Jeff Smith")
    (p:languages "Python" "C" "Haskell")
    (d:rating    "9.5")


Here's a contrived HTML4-style example:

    html

    (meta
        (title "Hello World!")
        (description "My Example Website!")
    )

    (div #header
        (a href="/"
            (img src="/logo.png" "Example.org Logo")
        )
    )

    (div #body
        (div.aside
            (p "Welcome to" (span.bold "Example Website!"))
        )
        (div.main
            (h1 #title "Hello World!")
        )
    )
    
    (div #foot
        (p "Copyright © Example Organisation")
    )


# Syntax and Semantics

A native Bach document is a 3-tuple of

 * a label: like an XML tag name
 * attributes: a mapping of attribute names to a list of values
 * children: a mixed list of strings and subdocuments

In terms of syntax, a Bach document is a non-empty string that may start with
#-style comments, followed by a label, then optionally attributes, shorthand
attributes, string literals, and subdocuments in any order. Subdocuments may
not contain #-style comments, but may contain #-style shorthand attributes
instead.

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
an empty string value. ***This behaviour changed for XML compatibility***

    (item anAttributeWithEmptyValue)

Subdocuments start and end with brackets. They are always non-empty.
String literals and subdocuments may always mix.

    document (subdocument "a literal" (anotherSubdocument) "another literal")

Bach string literals and subdocuments follow XHTML-style whitespace
normalisation rules for mixed content types (aka `xs:complexType mixed="true"`,
prevent this with `xml:space="preserve"`; you may like to configure Bach
with a dedicated shorthand syntax to do this).


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


## Important Security Considerations

While Bach itself is not vulnerable to
many common attacks on XML, such as exponential entity expansion (e.g. the
"Billion laughs" attack), it is possible that a Bach document *translated to
XML* may become a threat to an XML parser.

This reference implementation does not impose a limit on the length or
complexity of a parsed Bach document. It is possible to create a Denial
of Service (DoS) attack, or consume excessive processing time, if a server
does not limit the rate of access to a Bach parser.


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

