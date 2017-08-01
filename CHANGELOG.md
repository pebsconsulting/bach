# CHANGELOG

## 20170801

    * The colon ":" is no longer an optional way to define attribute values.

    This is to ensure better compatibility with XML namespaces.

    Attribute value assignemnts are still possible using equals e.g. foo="bar"


    * Portable formal grammar

    Created a machine-readable description of the grammar (grammar.txt) that
    can be compiled (cgrammar.py) into a compact state machine representation.

    By defining the Bach language in this way, it is portable and we don't have
    to re-write a representation of the rules in each programming language that
    we use to implement the parser. It is hoped this will also simplify the
    development of parsers, reduce human error, and make language enhancements
    easier to coordinate across parsers.

    Goals:
        * complete a concise rewrite of the Python parser using the compiled
          grammar
        * write a parser in C


## 20170730

    * Fix [issue #2](https://github.com/tawesoft/bach/issues/2)


## 20170722

    Bach Language Mission Statement

    Bach is a lisp-like language created by Tawesoft for general-purpose
    semantic document markup. It can be parsed directly, or translated to XML
    or Python literals.

    Bach as a language is a win for our purposes: writing hand-authored
    semantic documents for offline processing.

    XML has many decades of knowledge and tooling behind it. It was originally
    envisaged that Bach would provide feature-parity with XML features such as
    XLST, XQuery, DTD and XML Schemas. However, it is likely that "reinventing"
    these features for Bach would require a lot of effort for what would be
    only minor aesthetic improvements, missing out on exciting new developments
    such as RELAX NG.

    Therefore we resolve to make Bach the best language it can be for
    hand-authoring documents with a map both to and from XML for integration
    with existing XML tooling.

    Watch for these changes to \
   [Bach on GitHub](https://github.com/tawesoft/bach)

