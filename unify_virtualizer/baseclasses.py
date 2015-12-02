#    Filename: baseclasses.py		 Created: 2015-08-28  11:27:19
#    This file was automatically created by a pyang plugin (PNC) developed at Ericsson Hungary Ltd., 2015
#    Authors: Robert Szabo, Balazs Miriszlai, Akos Recse, Raphael Vicente Rosa
#    Credits: Robert Szabo, Raphael Vicente Rosa, David Jocha, Janos Elek, Balazs Miriszlai, Akos Recse
#    Contact: Robert Szabo <robert.szabo@ericsson.com>
        
#    Yang file info:
#    Namespace: urn:unify:virtualizer
#    Prefix: virtualizer
#    Organization: ETH
#    Contact: Robert Szabo <robert.szabo@ericsson.com>
#    Revision: 2015-07-20
#    Description: Virtualizer's revised (simplified) data model

__copyright__ = "Copyright 2015, Ericsson Hungary Ltd."
__license__ = "Apache License, Version 2.0"

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import xml.etree.ElementTree as ET
from xml.dom.minidom import parseString
import copy
from types import *
from decimal import *
from collections import OrderedDict, Iterable

class Yang(object):
    """
    Class defining the root attributes and methods for all Virtualizer classes
    """
    def __init__(self, tag, parent=None):
        self._parent = parent
        self._tag = tag
        self._operation = None
        self._referred = [] # to hold leafref references for backward search
        self._sorted_children = [] # to hold children Yang list

    def get_parent(self):
        """
        Returns the parent in the class subtree.
        :return: Yang
        """
        return self._parent

    def set_parent(self, parent):
        """
        Set the parent to point to the next node up in the Yang class instance tree
        :param parent: Yang
        :return: -
        """
        self._parent = parent

    def get_tag(self):
        """
        Returns the YANG tag for the class.
        :return: string
        """
        return self._tag

    def set_tag(self, tag):
        """
        Set the YANG tag for the class
        :param tag: string
        :return: -
        """
        self._tag = tag

    def xml(self, ordered=True):
        """
        Dump the class subtree as XML string
        :return: string
        """
        root = self._et(None, False, ordered)
        xmlstr = ET.tostring(root, encoding="utf8", method="xml")
        dom = parseString(xmlstr)
        return dom.toprettyxml()

    def et(self):
        return self._et(None, False, True)

    def get_as_text(self, ordered=True):
        """
        Dump the class subtree as TEXT string
        :return: string
        """
        root = self._et(None, False, ordered)
        return ET.tostring(root, encoding="utf8", method="html")

    def _parse(self, parent, root):
        """
        Abstract method to create classes from XML string
        :param parent: Yang
        :param root: ElementTree
        :return: -
        """
        pass

    def reduce(self, reference, ignores=None):
        """
        Delete instances which equivalently exist in the reference tree.
        The call is recursive, a node is removed if and only if all of its children are removed.
        :param reference: Yang
        :return: True if object to be removed otherwise False
        """
        _reduce = True
        _ignores = ["_parent", "_tag", "_sorted_children", "_referred", "_key_attributes"]
        if ignores is not None:
            if type(ignores) is tuple:
                _ignores.extend(ignores)
            else:
                _ignores.append(ignores)
        for k, v in self.__dict__.items():
            # if hasattr(v, "mandatory") and v.get_mandatory() is True:
            #     _ignores.append(k)
            if type(self._parent) is ListYang: # todo: move this outside
                if k == self.keys():
                    _ignores.append(k)
            if k not in _ignores:
                if isinstance(v, Yang):
                    if k in reference.__dict__.keys():
                        if type(v) == type(reference.__dict__[k]):
                            if v.reduce(reference.__dict__[k]):
                                v.delete()
                            else:
                                _reduce = False
                elif v != reference.__dict__[k]:  # to handle _operation, etc.
                    _reduce = False
        return _reduce

    def get_path(self):
        """
        Returns the complete path (since the root) of the instance of Yang
        :param: -
        :return: string
        """
        if self.get_parent() is not None:
            return self.get_parent().get_path() + "/" + self.get_tag()
        else:
            return "/" + self.get_tag()

    def walk_path(self, path):
        """
        Follows the specified path to return the instance it represents
        :param path: string
        :return: attribute instance of Yang
        """
        if path == "":
            return self

        p = path.split("/")
        l = p.pop(0)
        if path[0] == "/": # absolute path
            if self.get_parent() is not None:
                return self.get_parent().walk_path(path)
            elif self.get_tag() == p[0]:
                p.pop(0)
                return self.walk_path("/".join(p))
            raise ValueError("Root tag not found in walk_path()")
        if l == "..":
            return self.get_parent().walk_path("/".join(p))
        else:
            if (l.find("[") > 0) and (l.find("]") > 0):
                attrib = l[0: l.find("[")]
                keystring = l[l.find("[") + 1: l.rfind("]")]
                key = list()
                keyvalues = keystring.split(",")
                for kv in keyvalues:
                    v = kv.split("=")
                    key.append(v[1])
                if len(key) == 1:
                    return getattr(self, attrib)[key[0]].walk_path("/".join(p))
                else:
                    return getattr(self, attrib)[key].walk_path("/".join(p))
            else:
                return getattr(self, l).walk_path("/".join(p))

    def get_rel_path(self, target):
        """
        Returns the relative path from self to the target
        :param target: instance of Yang
        :return: string
        """
        src = self.get_path()
        dst = target.get_path()
        s = src.split("/")
        d = dst.split("/")
        if s[0] != d[0]:
            return dst
        i = 1
        ret = list()
        while s[i] == d[i]:
            i += 1
        for j in range(i, len(s)):
            ret.insert(0, "..")
        for j in range(i, len(d)):
            ret.append(d[j])
        return '/'.join(ret)

    @classmethod
    def parse(cls, parent=None, root=None):
        """
        Class method to create virtualizer from XML string
        :param parent: Yang
        :param root: ElementTree
        :return: class instance of Yang
        """
        temp = cls(root.tag, parent=parent)
        temp._parse(parent, root)
        return temp

    def _et(self, node, inherited=False, ordered=True):
        """
        Inserts node as subelement of current ElementTree or create a new tree if it is not initialized
        param node: reference to the node element 
        return: Element of ElementTree
        """
        _prohibited = ["_tag", "_sorted_children", "_key_attributes", "_referred"]
        attribs = {}
        for key, item in self.__dict__.items():
            if not isinstance(item, Yang):
                if item is not None and key not in _prohibited:
                    attribs[key.translate(None, '_')] = item

        if self.is_initialized():
            if node is not None:
                node = ET.SubElement(node, self.get_tag(), attrib=attribs)
            else:
                node = ET.Element(self.get_tag(), attrib=attribs)
            if len(self._sorted_children) > 0:
                for c in self._sorted_children:
                    if self.__dict__[c] is not None:
                        self.__dict__[c]._et(node, inherited, ordered)
        else:
            if node is None:
                node = ET.Element(self.get_tag(), attrib=attribs)

        return node

    def __str__(self):
        """
        Overide str methor to dump the class subtree as XML string
        :return: string
        """
        return self.xml()

    def contains_operation(self, operation="delete"):  # FIXME: rename has_operation()
        """
        Verifies if the instance contains operation set for any of its attributes
        :param operation: string
        :return: boolean
        """
        if self.get_operation() == operation:
            return True
        for k, v in self.__dict__.items():
            if isinstance(v, Yang) and k is not "_parent":
                if v.contains_operation(operation):
                    return True
        return False

    def get_operation(self):
        """
        Returns the _operation attribute
        :param: -
        :return: string
        """
        return self._operation

    def set_operation(self, operation="delete"):
        """
        Defines operation for instance
        :param operation: string
        :return: -
        """
        self._operation = operation
        for k, v in self.__dict__.items():
            if isinstance(v, Yang) and k is not "_parent":
                v.set_operation(operation)

    def is_initialized(self):
        """
        Check if any of the attributes of instance are initialized, returns True if yes
        :param: -
        :return: boolean
        """
        for k, v in self.__dict__.items():
            if isinstance(v, Yang) and k is not "_parent":
                if v.is_initialized():
                    return True
        return False

    def __eq__(self, other):
        """
        Check if all the attributes and class attributes are the same in instance and other, returns True if yes
        :param other: instance of Yang
        :return: boolean
        """
        eq = True
        # Check attributes
        self_atribs = self.__dict__
        other_atribs = other.__dict__
        eq = eq and (self_atribs.keys().sort() == other_atribs.keys().sort())
        if eq:
            for k in self_atribs.keys():
                if k is not "_parent":
                    for k_ in other_atribs.keys():
                        if k == k_:
                            eq = eq and (self_atribs[k] == other_atribs[k_])
        # Check class attributes
        self_class_atribs = self.__class__.__dict__
        other_class_atribs = other.__class__.__dict__
        eq = eq and (self_class_atribs.keys().sort() == other_class_atribs.keys().sort())
        if eq:
            for k in self_class_atribs.keys():
                for k_ in other_class_atribs.keys():
                    if k == k_ and not callable(self_class_atribs[k]):
                        eq = eq and (self_class_atribs[k] == other_class_atribs[k_])
        return eq

    def __merge__(self, source, execute=False):
        """
        Common recursive functionaltify for merge() and patch() methods. Execute defines if operation is copied or executed.
        :param source: instance of Yang
        :param execute: True - operation is executed; False - operation is copied
        :return: -
        """
        if execute and source.get_operation() == 'delete':
            self.delete()
            return

        for k, v in source.__dict__.items():
            if k is not "_parent":
                if k not in self.__dict__.keys():
                        self.__dict__[k] = copy.deepcopy(v)
                        self.__dict__[k].set_parent(self)
                else:
                    if isinstance(v, Yang):
                        self.__dict__[k].__merge__(v, execute)
                    else:
                        if v != self.__dict__[k]:
                            self.__dict__[k] = copy.deepcopy(v)


    def merge(self, source):
        """
        Merge source into the instance recursively; source remains unchanged.
        :param source: instance of Yang
        :return: -
        """
        self.__merge__(source, False)

    def patch(self, source):
        """
        Method to process diff changeset, i.e., merge AND execute operations in the diff. For example, operation = delete removes the yang object.        :param diff: Yang
        :return: -
        """
        self.__merge__(source, True)

    def empty_copy(self):
        """
        Performs copy of instance of Yang
        :param: -
        :return: instance copy (of Yang)
        """
        return self.__class__(self._tag)

    def full_copy(self):
        """
        Performs deepcopy of instance of Yang
        :param: -
        :return: instance copy (of Yang)
        """
        return copy.deepcopy(self)

    def delete(self):  # FIXME: if referred by a LeafRef?
        """
        Remove element when ListYang and set to None when Leaf
        :param: -
        :return: -
        """
        if self.get_parent() is not None:
            if isinstance(self, ListedYang):
                self.get_parent().remove(self)
            else:
                self.get_parent().__dict__[self.get_tag()] = None  # FIXME: tag is not necessarily Python naming conform!

    def set_referred(self, leaf_ref):
        """
        Append in referred names of leafs referred (children of) by instance of Yang
        :param leaf_ref: LeafRef
        :return: -
        """
        if leaf_ref not in self._referred:
            self._referred.append(leaf_ref)

    def unset_referred(self, leaf_ref):
        """
        Append in referred names of leafs referred (children of) by instance of Yang
        :param leaf_ref: LeafRef
        :return: -
        """
        if leaf_ref in self._referred:
            self._referred.remove(leaf_ref)

    def bind(self, relative=False):
        """
        Binds all elements of self attributes
        :param: relative: Boolean
        :return: -
        """
        if len(self._sorted_children) > 0:
            for c in self._sorted_children:
                if self.__dict__[c] is not None:
                    self.__dict__[c].bind(relative)
        return

    def _parse(self, parent, root):
        """
        Abstract method to create classes from XML string
        :param parent: Yang
        :param root: ElementTree
        :return: -
        """
        for key, item in self.__dict__.items():
            if key is not "_parent":
                if isinstance(item, Leaf):
                    item.parse(root)
                elif isinstance(item, ListYang):
                    object_ = root.find(key)
                    itemClass = item.get_type()
                    while object_ is not None:
                        itemparsed = itemClass.parse(self, object_)
                        if "operation" in object_.attrib.keys():
                            itemparsed.set_operation(object_.attrib["operation"])
                            # itemparsed.set_operation(object_.attrib["operation"])
                        self.__dict__[key].add(itemparsed)
                        root.remove(object_)
                        object_ = root.find(key)
                elif isinstance(item, Yang):
                    object_ = root.find(key)
                    if object_ is not None:
                        item._parse(self, object_)
                        if "operation" in object_.attrib.keys():
                            self.set_operation(object_.attrib["operation"])
                            # self.set_operation(object_.attrib["operation"])

    def diff(self, target):
        """
        Method to return an independent changeset between target and the instance (neither the instance nor the target is modified).
        :param target: Yang
        :return: Yang
        """
        diff = copy.deepcopy(target)
        diff.reduce(self)
        return diff


class Leaf(Yang):
    """
    Class defining Leaf basis with attributes and methods
    """
    def __init__(self, tag, parent=None):
        super(Leaf, self).__init__(tag, parent)
        self.data = None
        """:type: ???"""
        self.mandatory = False
        """:type: boolean"""
        self.units = ""
        """:type: string"""

    def get_as_text(self):
        """
        Abstract method to get data as text
        """
        pass

    def get_value(self):
        """
        Abstract method to get data value
        """
        pass

    def set_value(self, value):
        """
        Abstract method to set data value
        """
        pass

    def get_units(self):
        """
        Return self.units
        :return: string
        """
        return self.units

    def set_units(self, units):
        """
        Set self.units
        :param units:
        :return: -
        """
        self.units = units

    def get_mandatory(self):
        """
        Return self.mandatory
        :return: string
        """
        return self.mandatory

    def set_mandatory(self, mandatory):
        """
        Set self.mandatory
        :param mandatory:
        :return: -
        """
        self.mandatory = mandatory

    def is_initialized(self):
        """
        Overides Yang method to check if data contains value
        :param: -
        :return: boolean
        """
        if self.data is not None:
            return True
        return False

    def _et(self, parent, inherited=False, ordered=True):
        """
        Overides Yang method return parent with subelement as leaf tag and data as text if it is initialized
        :param parent: ElementTree
        :return: Element of ElementTree
        """
        if self.is_initialized():
            if type(self.data) is ET.Element:
                parent.append(self.data)
            else:
                e_data = ET.SubElement(parent, self.get_tag())
                e_data.text = self.get_as_text()+self.get_units()
        return parent

    def clear_data(self):
        """
        Erases data defining it as None
        :param: -
        :return: -
        """
        self.data = None

    def delete(self):
        """
        Erases data defining it as None
        :param: -
        :return: -
        """
        self.data = None

    def reduce(self, reference):
        """
        Overides Yang method to reduce other, return True if its data if different from self.data or _operation attributes mismatch
        :param reference: instance of Yang
        :return: boolean
        """
        if isinstance(self.data, ET.Element):
            if (ET.tostring(self.data) != ET.tostring(reference.data)) \
                    or (self.get_operation() != reference.get_operation()) \
                    or self.contains_operation("delete"):
                return False
        else:
            if (self.data != reference.data) \
                    or (self.get_operation() != reference.get_operation()) \
                    or self.contains_operation("delete"):
                return False
        return True

    def __eq__(self, other):
        """
        Check if other leaf has the same attributes and values, returns True if yes
        :param other: instance
        :return: boolean
        """
        eq = True
        for k, v in self.__dict__.items():
            if k is not "_parent":
                eq = eq and (hasattr(other, k)) and (v == other.__dict__[k])
        return eq

    def patch(self, candidate):
        # not sure if all attributes have to be overwritten, or just self.data
         for k, v in self.__dict__.items():
            if k is not "_parent":
                for k_, v_ in candidate.__dict__.items():
                    if k == k_:
                        self.__dict__[k] = candidate.__dict__[k]
                        break

class StringLeaf(Leaf):
    """
    Class defining Leaf with string extensions
    """
    def __init__(self, tag, parent=None, value=None, units="", mandatory=False): # FIXME: why having units for StringLeaf?
        super(StringLeaf, self).__init__(tag, parent=parent)
        self.set_value(value)
        """:type: string"""
        self.set_units(units)
        """:type: string"""
        self.set_mandatory(mandatory) # FIXME: Mandatory should be handled in the Leaf class!
        """:type: boolean"""

    def parse(self, root):
        """
        Abstract method to create instance class StringLeaf from XML string
        :param root: ElementTree
        :return: -
        """
        e_data = root.find(self.get_tag())
        if e_data is not None:
            if len(e_data._children) > 0:
                for i in e_data.iter():
                    i.tail = None
                e_data.text = None
                self.data = e_data
            else:
                self.set_value(e_data.text)
            root.remove(e_data)

    def get_as_text(self):
        """
        Returns data value as text
        :param: -
        :return: string
        """
        if type(self.data) == ET:
            return ET.tostring(self.data, encoding="us-ascii", method="text")
        return self.data

    def get_value(self):
        """
        Returns data value
        :param: -
        :return: string
        """
        return self.data

    def set_value(self, value):
        """
        Sets data value
        :param value: string
        :return: -
        """
        self.data = value


class IntLeaf(Leaf):
    """
    Class defining Leaf with integer extensions (e.g., range)
    """
    def __init__(self, tag, parent=None, value=None, int_range=[], units="", mandatory=False):
        super(IntLeaf, self).__init__(tag, parent=parent)
        self.int_range = int_range
        self.data = None
        """:type: int"""
        if value is not None:
            self.set_value(value)
        self.set_units(units)
        """:type: string"""
        self.set_mandatory(mandatory)
        """:type: boolean"""

    def parse(self, root):
        """
        Creates instance IntLeaf setting its value from XML string
        :param root: ElementTree
        :return: -
        """
        def check_int(s):
            if s[0] in ('-', '+'):
                return s[1:].isdigit()
            return s.isdigit()

        e_data = root.find(self.get_tag())
        if e_data is not None:
            if len(e_data._children) > 0:
                for i in e_data.iter():
                    i.tail = None
                e_data.text = None
                self.data = e_data  # ?? don't know if need to replace as others
            else:
                if self.units != "":
                    for c in range(0, len(e_data.text)):
                        v = len(e_data.text)-c
                        st = e_data.text[:v]
                        if check_int(st):
                            self.set_value(st)
                            self.set_units(e_data.text[v:len(e_data.text)])
                            break
                else:
                    self.set_value(e_data.text)
            root.remove(e_data)
            self.initialized = True

    def get_as_text(self):
        """
        Returns data value as text
        :param: -
        :return: string
        """
        if type(self.data) == ET:
            return ET.tostring(self.data, encoding="us-ascii", method="text")
        return str(self.data)

    def get_value(self):
        """
        Returns data value
        :param: -
        :return: int
        """
        return self.data

    def set_value(self, value):
        """
        Sets data value as int
        :param value: int
        :return: -
        """
        if type(value) is not int:
            try:
                value = int(value)
            except TypeError:
                print "Cannot cast to integer!"
        if self.check_range(value):
            self.data = value
        else:
            print "Out of range!"

    def check_range(self, value):
        """
        Check if value is inside range limits
        :param value: int
        :return: boolean
        """
        for i in self.int_range:
            if type(i) is tuple:
                if value in range(i[0], i[1]):
                    return True
            else:
                if value == i:
                    return True
        return False


class Decimal64Leaf(Leaf):
    """
    Class defining Leaf with decimal extensions (e.g., dec_range)
    """
    def __init__(self, tag, parent=None, value=None, dec_range=[], fraction_digits=1, units="", mandatory=False):
        super(Decimal64Leaf, self).__init__(tag, parent=parent)
        self.dec_range = dec_range
        self.fraction_digits = fraction_digits
        self.data = None
        """:type: Decimal"""
        if value is not None:
            self.set_value(value)
        self.set_units(units)
        """:type: string"""
        self.set_mandatory(mandatory)
        """:type: boolean"""

    def parse(self, root):
        """
        Abstract method to instance class Decimal64Leaf from XML string
        :param root: ElementTree
        :return: -
        """
        e_data = root.find(self.get_tag())
        if e_data is not None:
            if len(e_data._children) > 0:
                for i in e_data.iter():
                    i.tail = None
                e_data.text = None
                self.data = e_data  # ?? don't know if need to replace as others
            else:
                self.set_value(e_data.text)
            root.remove(e_data)
            self.initialized = True

    def get_as_text(self):
        """
        Returns data value as text
        :param: -
        :return: string
        """
        if type(self.data) == ET:
            return ET.tostring(self.data, encoding="us-ascii", method="text")
        return str(self.data)

    def get_value(self):
        """
        Returns data value
        :param: -
        :return: decimal
        """
        return self.data

    def set_value(self, value):
        """
        Sets data value as decimal
        :param value: decimal
        :return: -
        """
        if type(value) is not Decimal:
            try:
                value = Decimal(value)
            except TypeError:
                print "Cannot cast to Decimal!"
        if self.check_range(value):
            self.data = value
        else:
            print "Out of range!"

    def check_range(self, value):
        """
        Check if value is inside range limits
        :param value: decimal
        :return: boolean
        """
        for i in self.dec_range:
            if type(i) is tuple:
                if value in range(i[0], i[1]):
                    return True
            else:
                if value == i:
                    return True
        return False

class BooleanLeaf(Leaf):
    """
    Class defining Leaf with boolean extensions (e.g., True or False)
    """
    def __init__(self, tag, parent=None, value=None, units="", mandatory=False):
        super(BooleanLeaf, self).__init__(tag, parent=parent)
        self.data = None
        """:type: boolean"""
        if value is not None:
            self.set_value(value)
        self.set_units(units)
        """:type: string"""
        self.set_mandatory(mandatory)
        """:type: boolean"""

    def parse(self, root):
        """
        Abstract method to create instance class BooleanLeaf from XML string
        :param root: ElementTree
        :return: -
        """
        e_data = root.find(self.get_tag())
        if e_data is not None:
            if len(e_data._children) > 0:
                for i in e_data.iter():
                    i.tail = None
                e_data.text = None
                self.data = e_data  # ?? don't know if need to replace as others
            else:
                self.set_value(e_data.text)
            root.remove(e_data)
            self.initialized = True

    def get_as_text(self):
        """
        Returns data value as text
        :param: -
        :return: string
        """
        if type(self.data) == ET:
            return ET.tostring(self.data, encoding="us-ascii", method="text")
        return str(self.data).lower()

    def get_value(self):
        """
        Returns data value
        :param: -
        :return: int
        """
        return self.data

    def set_value(self, value):
        """
        Sets data value as decimal
        :param value: int
        :return: -
        """
        if value == "true":
            self.data = True
        elif value == "false":
            self.data = False
        else:
            raise TypeError("Not a boolean!")


class Leafref(StringLeaf):
    """
    Class defining Leaf extensions for stringleaf when its data references other instances
    """
    def __init__(self, tag, parent=None, value=None, units="", mandatory=False):
        self.target = None # must be before the super call as set_value() is overidden
        """:type: Yang"""
        # super call calls set_value()
        super(Leafref, self).__init__(tag, parent=parent, value=value, mandatory=mandatory)

    def set_value(self, value):
        """
        Sets data value as either a path or a Yang object
        :param value: path string or Yang object
        :return: -
        """
        if value is None:
            self.unbind()
            self.data = None
            self.target = None
            return
        if type(value) is str:
            if self.data != value:
                self.unbind()
                self.target = None
                self.data = value
                # self.bind()
        elif issubclass(type(value), Yang):
            if self.target != value:
                self.unbind()
                self.data = None
                self.target = value
                self.target.set_referred(self)
                # self.bind()
        else:
            raise ValueError("Leafref value is of unknown type.")

    def is_initialized(self):
        """
        Overides Leaf method to check if data contains data and target is set
        :param: -
        :return: boolean
        """
        if (self.data is not None) or (self.target is not None):
            return True
        else:
            return False

    def get_as_text(self):
        """
        If data return its value as text, otherwise get relative path to target
        :param: -
        :return: string
        """
        if self.data is not None:
            return self.data
        if self.target is not None:
            self.bind()
            return self.data
        else:
            raise ReferenceError("Leafref get_as_text() is called but neither data nor target exists.")

    def get_target(self):
        """
        Returns get path to target if data is initialized
        :param: -
        :return: string
        """
        if self.target is None:
            self.bind() # sets the target
        return self.target
        # if self.data is not None:
        #     return self.walk_path(self.data)

    def bind(self, relative=False):
        """
        Binds the target and add the referee to the referende list in the target. The path is updated to relative or absolut based on the parameter
        :param: relative: Boolean
        :return: -
        """
        if self.target is not None:
            if relative:
                self.data = self.get_rel_path(self.target)
            else:
                self.data = self.target.get_path()
        elif self.data is not None:
            if self._parent is not None:
                self.target = self.walk_path(self.data)
                self.target.set_referred(self)

    def unbind(self):
        if self.target is not None:
            self.target.unset_referred(self)


class ListedYang(Yang):
    """
    Class defined for Virtualizer classes inherit when modeled as list
    """
    def __init__(self, tag, keys, parent=None):
        super(ListedYang, self).__init__(tag, parent)
        self._key_attributes = keys

    def get_parent(self):
        """
        Returns parent`s parent of ListedYang
        :param: -
        :return: instance of Yang
        """
        return self._parent.get_parent()

    def keys(self):
        """
        Abstract method to get identifiers of class that inherit ListedYang 
        """
        if len(self._key_attributes) > 1:
            keys = []
            for k in self._key_attributes:
                keys.append(self.__dict__[k].get_value())
            return tuple(keys)
        return self.__dict__[self._key_attributes[0]].get_value()

    def get_key_tags(self):
        """
        Abstract method to get tags of class that inherit ListedYang 
        """
        if len(self._key_attributes) > 1:
            tags = []
            for k in self._key_attributes:
                tags.append(self.__dict__[k].get_tag())
            return tuple(tags)
        return self.__dict__[self._key_attributes[0]].get_tag()

    def get_path(self):
        """
        Returns path of ListedYang based on tags and values of its components
        :param: -
        :return: string
        """
        key_values = self.keys()
        if key_values is None:
            raise KeyError("List entry without key value: " + self.get_as_text())
        key_tags = self.get_key_tags()
        if type(key_tags) is tuple:
            s = ', '.join('%s=%s' % t for t in zip(key_tags, key_values))
        else:
            s = key_tags + "=" + key_values
        if self.get_parent() is not None:
            return self.get_parent().get_path() + "/" + self.get_tag() + "[" + s + "]"
        else:
            return self.get_tag() + "[" + s + "]"

    def empty_copy(self):
        """
        Performs copy of instance defining its components with deep copy
        :param: -
        :return: instance
        """
        inst = self.__class__()
        for key in self._key_attributes:
            setattr(inst, key, getattr(self, key))
        return inst

    def reduce(self, reference):
        """
        Delete instances which equivalently exist in the reference tree.
        The call is recursive, a node is removed if and only if all of its children are removed.
        :param reference: Yang
        :return:
        """
        keys = self.get_key_tags()
        return super(ListedYang, self).reduce(reference, keys)



        # for k, v in self.__dict__.items():
        #     if k != "_parent" and k != "_operation" and not v in keys:
        #         if isinstance(v, Yang):
        #             if k in reference.__dict__.keys():
        #                 if type(v) == type(reference.__dict__[k]):
        #                     v.reduce(reference.__dict__[k])


class ListYang(Yang):  # FIXME: to inherit from OrderedDict()
    """
    Class to express list as dictionary 
    """
    def __init__(self, tag, parent=None, type=None):
        super(ListYang, self).__init__(tag, parent)
        self._data = OrderedDict()
        self._type = type

    def get_type(self):
        """
        Returns class which references elements of _data OrderedDict
        :param: -
        :return: Yang subclass
        """
        return self._type

    def set_type(self, type):
        """
        Sets class which references elements of _data OrderedDict
        :param: Yang subclass
        :return: -
        """
        self._type = type

    def keys(self):
        """
        Returns indices of ListYang dictionary 
        :param: -
        :return: list
        """
        return self._data.keys()

    def values(self):
        """
        Returns values of ListYang dictionary
        :param: -
        :return: list
        """
        return self._data.values()

    def iterkeys(self):
        """
        Returns iterator of keys of ListYang dictionary 
        :param: -
        :return: iterator
        """
        return self._data.iterkeys()

    def itervalues(self):
        """
        Returns iterator of values of ListYang dictionary 
        :param: -
        :return: list
        """
        return self._data.itervalues()

    def items(self):
        """
        Returns items of ListYang dictionary 
        :param: -
        :return: list
        """
        return self._data.items()

    def iteritems(self):
        """
        Returns iterator of items of ListYang dictionary 
        :param: -
        :return: list
        """
        return self._data.iteritems()

    def has_key(self, key):  # PEP8 wants it with 'in' instead of 'has_key()'
        """
        Returns if key is in ListYang dictionary 
        :param key: string
        :return: boolean
        """
        return key in self._data.keys()

    def has_value(self, value):
        """
        Returns if value is in ListYang dictionary values
        :param value: string or instance
        :return: boolean
        """
        return value in self._data.values()

    def length(self):
        """
        Returns length of ListYang dictionary
        :param: -
        :return: int
        """
        return len(self._data)

    def is_initialized(self):
        """
        Returns if ListYang dictionary contains elements
        :param: -
        :return: boolean
        """
        if len(self._data) > 0:
            return True
        return False

    def add(self, item):
        """
        add single or a list of items
        :param item: a single ListedYang or a list of ListedYang derivates
        :return: item
        """
        if type(item) is list or type(item) is tuple:
            for i in item:
                if isinstance(i, ListedYang):
                    self.add(i)
                else:
                    raise TypeError("Item must be ListedYang or a list of ListedYang!")
        elif isinstance(item, ListedYang):
            item.set_parent(self)
            self[item.keys()] = item
        else:
            raise TypeError("Item must be ListedYang or a list of ListedYang!")
        return item

    def remove(self, item):
        '''
        remove a single element from the list based on a key or a ListedYang
        :param item: key (single or composit) or a ListedYang
        :return: item
        '''
        if isinstance(item, ListedYang):
            item = item.keys()
        return self._data.pop(item)

    def _et(self, node, inherited=False, ordered=True):
        """
        Overides Yang method to each ListYang component be defined as SubElement of ElementTree
        :param node: ElementTree
        :return: ElementTree
        """
        if ordered:
            ordered_keys = sorted(self.keys())
            for k in ordered_keys:
                self._data[k]._et(node, ordered)
        else:
            for v in self.values():
                v._et(node, ordered)
        return node
        # for v in self.values():
        #     v._et(node)
        # return node

    def __iter__(self):  # ???
        """
        Returns iterator of ListYang dict
        :param: -
        :return: iterator
        """
        return self._data.__iter__()

    def next(self):
        """
        Go to next element of ListYang dictionary
        :param: -
        :return: -
        """
        self._data.next()

    def __getitem__(self, key):
        """
        Returns ListYang value if key in dictionary
        :param key: string
        :return: instance
        """
        if type(key) is list:
            key = tuple(key)
        if key in self._data.keys():
            return self._data[key]
        else:
            raise KeyError("key not existing")

    def __setitem__(self, key, value):
        """
        Fill ListYang dict with key associated to value
        :param key: string
        :param value: string or instance
        :return: -
        """
        self._data[key] = value
        value.set_parent(self)

    def clear_data(self):
        """
        Clear ListYang dict
        :param: -
        :return: -
        """
        self._data = dict()

    def reduce(self, reference):
        """
        Check if all keys of reference are going to be reduced and erase their values if yes
        :param reference: ListYang
        :return: boolean
        """
        _reduce = True
        for key in self.keys():
            if key in reference.keys():
                if self[key].reduce(reference[key]):
                    self[key].delete()
                else:
                    _reduce = False
            else:
                _reduce = False
        return _reduce

    def __merge__(self, source, execute=False):

        for item in source.keys():
            if item not in self.keys():
                self.add(copy.deepcopy(source[item]))  # it should be a full_copy()
            else:
                if isinstance(self[item], Yang) and type(self[item]) == type(source[item]):
                    # self[item].set_operation(target[item].get_operation())
                    self[item].__merge__(source[item], execute)

    def __eq__(self, other):
        """
        Check if dict of other ListYang is equal 
        :param other: ListYang
        :return: boolean
        """
        if self._data == other._data:
            return True
        return False

    def contains_operation(self, operation):
        """
        Check if any of items have operation set
        :param operation: string
        :return: boolean
        """
        for key in self._data.keys():
            if self._data[key].contains_operation(operation):
                return True
        return False

    def set_operation(self, operation="delete"):
        """
        Set operation for all of items in ListYang dict`
        :param operation: string
        :return: -
        """
        super(ListYang, self).set_operation(operation)
        for key in self._data.keys():
            self._data[key].set_operation(operation)

    def bind(self, relative=False):
        for v in self.values():
            v.bind(relative)


class FilterYang(Yang):
    def __init__(self, filter):
        # super(FilterYang, self).__init__()
        self.target = None
        self.result = None
        self.filter_xml = filter

    def run(self, yang):
        if self.filter_xml is not None:
            for child in self.filter_xml:
                self.result = self.walk_yang(child, yang, self.result)
        else:
            self.result = yang
        return self.result

    def walk_yang(self, filter, target, result):
        if target._tag == filter.tag: # probably double check
            if isinstance(target, Iterable):

                if len(filter) > 0:
                    result = target.empty_copy()
                    for target_child in target:
                        for filter_child in filter:
                            result.add(self.walk_yang(filter_child,
                                                      target_child,
                                                      None))
                else:
                    for target_child in target:
                        result.add(target_child)
                return result
            else:
                if len(filter) > 0:
                    result = target.empty_copy()
                    for filter_child in filter: # probably double check
                        if filter_child.tag in target.__dict__:
                            result.__dict__[filter_child.tag] = self.walk_yang(filter_child,
                                                                               target.__dict__[filter_child.tag],
                                                                               result.__dict__[filter_child.tag])
                    return result
                else:
                    return target.full_copy()

    def __str__(self):
        return ET.tostring(self.filter_xml)

    def xml(self): #FIXME have to remove!
        return self.filter_xml

    def set_filter(self, filter):
        self.filter_xml = filter

    def get_filter(self):
        return self.filter_xml
