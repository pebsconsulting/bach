DEFAULT_BUFFER_SIZE = (64*1024) # 64kb

from itertools import tee, zip_longest



def reader(src, bufsize):
    """Depending on the type of `src`, return the best lazy reader, a
       function that returns some iterable."""

    def readStream():
        while True:
            data = src.read(bufsize)
            if not data:
                return
            elif not len(data):
                yield data
                return
            else:
                yield from data

    def identity():
        return src

    def readIterable():
        return iter(src)

    if isinstance(src, str):
        return identity
    elif hasattr(src, "read"):
        return readStream
    elif hasattr(src, __iter__):
        return readIterable
    else:
        raise TypeError("src must be a text stream, str, or iterable")



def pairwise(iterable):
    """For [a, b, c, ...] lazily return [(a, b), (b, c), (c, ...), (..., None)]

    From Itertools Recipes in the Python 3 documentation:
    https://docs.python.org/3/library/itertools.html#itertools-recipes
    """
    a, b = tee(iterable)
    next(b, None)
    return zip_longest(a, b)



class stack():
    """Generic implementation of a stack interface backed by a list"""

    def __init__(self, xs=[]):
        self.entries = xs

    def peek(self, index=-1):
        try:
            return self.entries[index]
        except IndexError:
            return None

    def pop(self):
        return self.entries.pop()

    def push(self, x):
        self.entries.append(x)

    def __contains__(self, x):
        return (x in self.entries)



