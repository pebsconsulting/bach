import bach

# HTML-style shorthands
shorthands = [
    # HTML classes are an ordered set, because classes shouldn't repeat
    bach.Shorthand(".", "class", set),

    # HTML IDs don't have a collection type, because only one can appear
    bach.Shorthand("#", "id"),

    # As a contrived example, lets invent a shorthand for flags like
    # "$feature1 $feature2", where options can appear multiple times separated
    # by semicolons
    bach.Shorthand("$", "feature", list, '; '),
]

# Configure the parser to use these shorthands
foo = bach.Parser(shorthands)



