# Example of parsing two Bach documents, converting them to XML,
# and using XPath to query them then do something with the result

# One document is a list of quotes in "mixed-content" style with the text
# mixed with the author and date.

# The other has the text marked up seperately.

# with thanks to AdrianKoshka for the example documents


import bach
import sys
import random
from collections import namedtuple
from lxml import etree as ET


Quote = namedtuple('Quote', ['text', 'author', 'date'])

mixed_quotes = '''

list

(quote "Only Thing We Have to Fear Is Fear Itself."
  (author "Franklin Delano Roosevelt")
  (date "1933-03-04")
  "This is" (b "extra") "quote text as an example."
)

(quote "I believe that freedom is the deepest need of every human soul."
  (author "George W. Bush")
  (date "2004-04-13")
  "This is" (b "extra") "quote text as an example."
)

(quote "We don't wage war, but we are called upon to impose a peaceful solution."
  (author "Gerhard Schröder")
  (date "1999-03-24")
  "This is" (b "extra") "quote text as an example."
)
'''

# This converts into XML like:

# <?xml version='1.0' encoding='utf-8'?>
# <list>
#   <quote>Only Thing We Have to Fear Is Fear Itself.<author>Franklin Delano Roosevelt</author><date>1933-03-04</date></quote>
#   <quote>I believe that freedom is the deepest need of every human soul.<author>George W. Bush</author><date>2004-04-13</date></quote>
#   <quote>We don't wage war, but we are called upon to impose a peaceful solution.<author>Gerhard Schröder</author><date>1999-03-24</date></quote>
# </list>


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


# This converts into XML like:

# <?xml version='1.0' encoding='utf-8'?>
# <list>
#   <quote>
#     <author>Franklin Delano Roosevelt</author>
#     <date>1933-03-04</date>
#     <text>Only Thing We Have to Fear Is Fear Itself.</text>
#   </quote>
#   <quote>
#     <author>George W. Bush</author>
#     <date>2004-04-13</date>
#     <text>I believe that freedom is the deepest need of every human soul.</text>
#   </quote>
#   <quote>
#     <author>Gerhard Schröder</author>
#     <date>1999-03-24</date>
#     <text>We don't wage war, but we are called upon to impose a peaceful solution.</text>
#   </quote>
# </list>



parser = bach.Parser()


document1 = parser.parse(mixed_quotes)
tree1 = document1.toElementTree(ET)
quotes1 = []

# Uncomment  these to print out the XML
#xml1 = ET.tostring(tree1, encoding='utf-8', pretty_print=True, xml_declaration=True)
#print(xml1.decode('utf-8'))

document2 = parser.parse(structured_quotes)
tree2 = document2.toElementTree(ET)
quotes2 = []

# Uncomment these to print out the XML
#xml2 = ET.tostring(tree2, encoding='utf-8', pretty_print=True, xml_declaration=True)
#print(xml2.decode('utf-8'))


# Lets do the simpler case first, the one with standalone <text> nodes:

# Lets use XPATH to get all `list > quote` nodes quickly...
# Nice and elegant!!!

quoteNodes = tree2.xpath('/list/quote') # note, this can take a XML namespace argument too

for quoteNode in quoteNodes:
    # Lets use XPATH to get the attributes quickly again...
    text = quoteNode.xpath('text/text()')[0]
    author = quoteNode.xpath('author/text()')[0]
    date = quoteNode.xpath('date/text()')[0]
    quotes2.append(Quote(text=text, author=author, date=date))




# Lets do the other case now, the one with mixed content
# This one is trickier - because we actually have to iterate over the children
# of a node and decide how to handle the mixed content rather than just using XPath

# Lets use XPATH to get all `list > quote` nodes quickly...

quoteNodes = tree1.xpath('/list/quote') # note, this can take a XML namespace argument too

for quoteNode in quoteNodes:
    # In most cases, text is just the first element
    text = [quoteNode.text]
    
    # But a mixed document can have it anywhere really...
    # In this case, we'll ignore anything inside tagged author or date
    for node in quoteNode:
        if node.tag not in ('author', 'date'):
            text.append(node.text) # TODO really this should evalute the full text of the child node properly

        # Read about tail attribute at http://lxml.de/tutorial.html#elements-contain-text
        if node.tail:
            text.append(node.tail)

    text = ' '.join(text)

    # Lets use XPATH to get the other attributes quickly again...
    author = quoteNode.xpath('author/text()')[0]
    date = quoteNode.xpath('date/text()')[0]
    quotes1.append(Quote(text=text, author=author, date=date))




print("\nRandomly selected quote from document 1")
quote = random.choice(quotes1)
print("%s\nBy %s on %s" % (quote.text, quote.author, quote.date))

print("\nRandomly selected quote from document 2")
quote = random.choice(quotes2)
print("%s\nBy %s on %s" % (quote.text, quote.author, quote.date))







