
def toElementTree(etreeClass, bachDocument, parent=None):
    label, attributes, values = \
        bachDocument.label, bachDocument.attributes, bachDocument.children
    
    if parent is not None:
        e = etreeClass.SubElement(parent, label)
    else:
        e = etreeClass.Element(label)
    
    for k,v in attributes.items():
        e.set(k, v)

    lastElement = e
    for i in values:
        if type(i) is str:
            if lastElement == e:
                if lastElement.text:
                    lastElement.text += ' ' + i
                else:
                    lastElement.text = i
            else:
                if lastElement.tail:
                    lastElement.tail += ' ' + i
                else:
                    lastElement.tail = i
        else:
            e2 = toElementTree(etreeClass, i, e)
            lastElement = e2
    
    return e




