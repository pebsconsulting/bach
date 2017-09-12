# Example of parsing two Bach documents, and doing something with the result

# One document is a list of quotes in "mixed-content" style with the text
# mixed with the author and date.

# The other has the text marked up seperately.

# with thanks to AdrianKoshka for the example documents


import bach
import sys
import random
from collections import namedtuple


Quote = namedtuple('Quote', ['text', 'author', 'date'])

mixed_quotes = '''

list

(quote "Only Thing We Have to Fear Is Fear Itself."
  (author "Franklin Delano Roosevelt")
  (date "1933-03-04")
)

(quote "I believe that freedom is the deepest need of every human soul."
  (author "George W. Bush")
  (date "2004-04-13")
)

(quote "We don't wage war, but we are called upon to impose a peaceful solution."
  (author "Gerhard Schröder")
  (date "1999-03-24")
)
'''

structured_quotes = '''

list

(quote
  (author "Franklin Delano Roosevelt")
  (date "1933-03-04")
  (text "Only Thing We Have to Fear Is Fear Itself.")
)

(quote
  (author "George W. Bush")
  (date "2004-04-13")
  (text "I believe that freedom is the deepest need of every human soul.")
)

(quote
  (author "Gerhard Schröder")
  (date "1999-03-24")
  (text "We don't wage war, but we are called upon to impose a peaceful solution.")
)
'''


def parseMixedQuote(quote):
    date = "Unknown"
    author = "Unknown"

    assert quote.label == "quote"
    assert len(quote.children) > 1

    # first child is the text
    text = quote.children[0]
    assert type(text) is str

    # other nodes are tagged single values
    for tag in quote.children[1:]:
        assert type(tag) == bach.Document # works on latest only, comment out if error
        assert len(tag.children) == 1

        if tag.label == "date":
            date = tag.children[0]

        elif tag.label == "author":
            author = tag.children[0]

        else:
            raise RuntimeError("Unkown tag in quote: %s" % tag.label)

    return Quote(text=text, author=author, date=date)


def parseStructuredQuote(quote):
    text = None
    date = "Unknown"
    author = "Unknown"

    print(repr(quote))

    assert quote.label == "quote"
    assert len(quote.children) > 1

    # nodes are tagged single values
    for tag in quote.children:
        assert type(tag) == bach.Document # works on latest only, comment out if error
        assert len(tag.children) == 1

        if tag.label == "text":
            text = tag.children[0]

            # TODO the text node could be extended in future to support
            # additional structure, e.g. maybe Italics.

        elif tag.label == "date":
            date = tag.children[0]

        elif tag.label == "author":
            author = tag.children[0]

        else:
            raise RuntimeError("Unkown tag in quote: %s" % repr(tag.label))

    assert type(text) is str
    assert type(date) is str
    assert type(author) is str

    return Quote(text=text, author=author, date=date)



parser = bach.Parser()


document1 = parser.parse(mixed_quotes)

assert document1.label == "list"    

quotes1 = []

for quote in document1.children:
    quotes1.append(parseMixedQuote(quote))


document2 = parser.parse(structured_quotes)

assert document2.label == "list"    

quotes2 = []

for quote in document2.children:
    print(repr(quote))
    quotes2.append(parseStructuredQuote(quote))


print("\nRandomly selected quote from document 1")
quote = random.choice(quotes1)
print("%s\nBy %s on %s" % (quote.text, quote.author, quote.date))

print("\nRandomly selected quote from document 2")
quote = random.choice(quotes2)
print("%s\nBy %s on %s" % (quote.text, quote.author, quote.date))



