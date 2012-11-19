#    Document   : XmlDict.py
#    Package    : OTR Integration to XBMC
#    Author     : Frank Epperlein
#    Copyright  : 2005, Duncan McGreggor
#    License    : PSF
#    Description: XML-as-Dict Module


class XmlListConfig(list):
    def __init__(self, aList):
        for element in aList:
            if len(element):
                if len(element) == 1 or element[0].tag != element[1].tag:
                    self.append(XmlDict(element))
                elif element[0].tag == element[1].tag:
                    self.append(XmlListConfig(element))
            elif element.text:
                text = element.text.strip()
                if text:
                    self.append(text)


class XmlDict(dict):
    '''
    Example usage:

    >>> from xml.etree import ElementTree

    >>> tree = ElementTree.parse('your_file.xml')
    >>> root = tree.getroot()
    >>> xmldict = XmlDict(root)

    Or, if you want to use an XML string:

    >>> root = ElementTree.XML(xml_string)
    >>> xmldict = XmlDict(root)

    And then use xmldict for what it is... a dict.
    '''
    def __call__(self):
        return dict(self)

    def __init__(self, parent_element):
        childrenNames = [child.tag for child in parent_element.getchildren()]
        if parent_element.items():
            self.update(dict(parent_element.items()))
        for element in parent_element:
            if len(element):
                if len(element) == 1 or element[0].tag != element[1].tag:
                    aDict = XmlDict(element)
                else:
                    aDict = {element[0].tag: XmlListConfig(element)}
                if element.items():
                    aDict.update(dict(element.items()))
                if childrenNames.count(element.tag) > 1:
                    try:
                        currentValue = self[element.tag]
                        currentValue.append(aDict)
                        self.update({element.tag: currentValue})
                    except:
                        self.update({element.tag: [aDict]})
                else:
                    self.update({element.tag: aDict})
            elif element.items():
                self.update({element.tag: dict(element.items())})
            else:
                self.update({element.tag: element.text})



