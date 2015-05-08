# Copyright 2014 Levente Csikor <csikor@tmit.bme.hu>
# Copyright 2015 Janos Czentye <czentye@tmit.bme.hu>
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at:
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
Requirements::

  sudo apt-get install python-setuptools python-paramiko python-lxml \
  python-libxml2 python-libxslt1 libxml2 libxslt1-dev
  sudo pip install ncclient
"""
from pprint import pprint
from lxml import etree
from StringIO import StringIO
from ncclient import manager
from ncclient.operations import RPCError, OperationError
from ncclient.transport import TransportError
from ncclient.xml_ import new_ele, sub_ele


class AbstractNETCONFAdapter(object):
  """
  Abstract class for various Adapters rely on NETCONF protocol (RFC 4741)

  Contains basic functions for managing connection and invoking RPC calls

  Follows the Adapter design pattern
  """
  # NETCONF namespace
  NETCONF_NAMESPACE = u'urn:ietf:params:xml:ns:netconf:base:1.0'
  # RPC namespace. Must be set by derived classes
  _RPC_NAMESPACE = None

  def __init__ (self, server, port, username, password, timeout=30,
       debug=False):
    """
    Initialize connection parameters

    :param server: server address
    :type server: str
    :param port: port number
    :type port: int
    :param username: username
    :type username: str
    :param password: password
    :type password: str
    :param timeout: connection timeout (default=30)
    :type timeout: int
    :param debug: print DEBUG infos, RPC messages ect. (default: False)
    :type debug: bool
    :return: None
    """
    super(AbstractNETCONFAdapter, self).__init__()
    self.__server = server
    self.__port = int(port)
    self.__username = username
    self.__password = password
    self.__timeout = int(timeout)
    self.__debug = debug
    # variables for the last RPC reply
    self.__rpc_reply_formatted = dict()
    self.__rpc_reply_as_xml = ""
    # Server side and connection parameters
    self.__connection = None
    self.__config = None

  @property
  def RPC_NAMESPACE (self):
    """
    :return: Return specific RPC namespace
    :rtype: str
    """
    return self._RPC_NAMESPACE

  @RPC_NAMESPACE.setter
  def RPC_NAMESPACE (self, namespace):
    """
    :param namespace: Set specific RPC namespace
    :type namespace: str
    :return: None
    """
    self._RPC_NAMESPACE = unicode(namespace)

  @property
  def connected (self):
    """
    :return: Return connection state
    :rtype: bool
    """
    return self.__connection is not None and self.__connection.connected

  def connect (self):
    """
    This function will connect to the netconf server. The variable
    self.__connection is responsible for keeping the connection up.
    """
    self.__connection = manager.connect(host=self.__server, port=self.__port,
                                        username=self.__username,
                                        password=self.__password,
                                        hostkey_verify=False,
                                        timeout=self.__timeout)
    if self.__debug:
      print "Connecting to %s:%s with %s/%s ---> %s" % (
        self.__server, self.__port, self.__username, self.__password,
        'OK' if self.connected else 'PROBLEM')

  def disconnect (self):
    """
    This function will close the connection.

    :return: None
    """
    if self.connected:
      self.__connection.close_session()
    if self.__debug:
      print "Connection closed!"

  def get_config (self, source="running", to_file=False):
    """
    This function will download the configuration of the NETCONF agent in an
    XML format. If source is None then the running config will be downloaded.
    Other configurations are netconf specific (:rfc:`6241`) - running,
    candidate, startup

    :param source: NETCONF specific configuration source (defalut: running)
    :type source: str
    :param to_file: save config to file
    :type to_file: bool
    :return: None
    """
    if self.connected:
      self.__config = self.__connection.get_config(source=source).data_xml
      if to_file:
        with open("%s_%s.xml", "w") as f:
          f.write(self.__config)
      else:
        return self.__config
    else:
      raise RuntimeError("Not connected!")

  def get (self, expr="/proc/meminfo"):
    """
    This process works as yangcli's GET function. A lot of information can be
    got from the running NETCONF agent. If an xpath-based expression is also
    set, the results can be filtered. The results are not printed out in a
    file, it's only printed to stdout

    :param expr: xpath-based expression
    :type expr: str
    :return: result in XML
    :rtype: str
    """
    return self.__connection.get(filter=('xpath', expr)).data_xml

  def __remove_namespace (self, xml_element, namespace=None):
    """
    Own function to remove the ncclient's namespace prefix, because it causes
    "definition not found error" if OWN modules and RPCs are being used

    :param xml_element: XML element
    :type xml_element: str
    :param namespace: namespace
    :type namespace: str
    :return: cleaned XML elemenet
    """
    if namespace is not None:
      ns = u'{%s}' % namespace
      for elem in xml_element.getiterator():
        if elem.tag.startswith(ns):
          elem.tag = elem.tag[len(ns):]
    return xml_element

  def _create_rpc_body (self, rpc_name, options=None, switches=None, **params):
    """
    This function is devoted to create a raw RPC request message in XML format.
    Any further additional rpc-input can be passed towards, if netconf agent
    has this input list, called 'options'. Switches is used for connectVNF
    rpc in order to set the switches where the vnf should be connected.

    :param rpc_name: rpc name
    :type rpc_name: str
    :param options: additional RPC input in the specific <options> tag
    :type options: dict
    :param switches: set the switches where the vnf should be connected
    :type switches: list
    :param params: input params for the RPC using param's name as XML tag name
    :type params: dict
    :return: raw RPC message in XML format
    :rtype: str
    """
    # create the desired xml element
    xsd_fetch = new_ele(rpc_name)
    # set the namespace of your rpc
    xsd_fetch.set('xmlns', self.RPC_NAMESPACE)
    # set input params if they were set
    for k, v in params.iteritems():
      if isinstance(v, list):
        for element in v:
          sub_ele(xsd_fetch, k).text = str(element)
      else:
        sub_ele(xsd_fetch, k).text = str(v)
    # setting options if they were sent
    if options is not None:
      for k, v in options.iteritems():
        option_list = sub_ele(xsd_fetch, "options")
        sub_ele(option_list, "name").text = k
        sub_ele(option_list, "value").text = v
    # processing switches list
    if switches is not None:
      for switch in switches:
        sub_ele(xsd_fetch, "switch_id").text = switch
    # we need to remove the confusing netconf namespaces with our own function
    rpc_request = self.__remove_namespace(xsd_fetch, self.NETCONF_NAMESPACE)
    # show how the created rpc message looks like
    if self.__debug:
      print "Generated raw RPC message:\n", etree.tostring(rpc_request,
                                                           pretty_print=True)
    return rpc_request

  def __getChildren (self, element, namespace=None):
    """
    This is an inner function, which is devoted to automatically analyze the
    rpc-reply message and iterate through all the xml elements until the last
    child is found, and then create a dictionary. Return a dict with the
    parsed data.

    :param element: XML element
    :type element: str
    :param namespace: namespace
    :type: str
    :return: parsed XML data
    :rtype: dict
    """
    parsed = {}  # parsed xml subtree as a dict
    if namespace is not None:
      namespace = "{%s}" % namespace
    for i in element.iterchildren():
      if i.getchildren():
        # still has children! Go one level deeper with recursion
        val = self.__getChildren(i, namespace)
        key = i.tag.replace(namespace, "")
      else:
        # if <ok/> is the child, then it has only <rpc-reply> as ancestor
        # so we do not need to iterate through <ok/> element's ancestors
        if i.tag == "{%s}ok" % self.NETCONF_NAMESPACE:
          key = "rpc-reply"
          val = "ok"
        else:
          key = i.tag.replace(namespace, "")
          val = element.findtext(
            "%s%s" % (namespace, i.tag.replace(namespace, "")))
      if key in parsed:
        if isinstance(parsed[key], list):
          parsed[key].append(val)
        else:
          # had only one element, convert to list
          parsed[key] = [parsed[key], val]
      else:
        parsed[key] = val
    return parsed

  def rpc (self, rpc_name, options=None, switches=None, autoparse=True,
       **params):
    """
    This function is devoted to call an RPC, and parses the rpc-reply message
    (if needed) and returns every important parts of it in as a dictionary.
    Any further additional rpc-input can be passed towards, if netconf agent
    has this input list, called 'options'. Switches is used for connectVNF
    rpc in order to set the switches where the vnf should be connected.

    :param rpc_name: RPC function name
    :type rpc_name: str
    :param options: additional RPC input
    :type options: dict
    :param switches: set the switches where the vnf should be connected
    :type switches: list
    :param autoparse: automatically parse the rpc-reply (default: True)
    :type autoparse: bool
    :param params: additional input params for the RPC
    :type params: dict
    """
    request_data = self._create_rpc_body(rpc_name, options, switches, **params)
    # SENDING THE CREATED RPC XML to the server
    # rpc_reply = without .xml the reply has GetReply type
    # rpc_reply = with .xml we convert it to xml-string
    try:
      # we set our global variable's value to this xml-string therefore,
      # last RPC will always be accessible
      self.__rpc_reply_as_xml = self.__connection.dispatch(request_data).xml
    except (RPCError, TransportError, OperationError):
      raise
    # we have now the rpc-reply if autoparse is False, then we can gratefully
    # break the process of this function and return the rpc-reply
    if not autoparse:
      return self.__rpc_reply_as_xml
    # in order to handle properly the rpc-reply as an xml element we need to
    # create a new xml_element from it, since another BRAINFUCK arise around
    # namespaces
    # CREATE A PARSER THAT GIVES A SHIT FOR NAMESPACE
    parser = etree.XMLParser(ns_clean=True)
    # PARSE THE NEW RPC-REPLY XML
    dom = etree.parse(StringIO(self.__rpc_reply_as_xml), parser)
    # dom.getroot() = <rpc_reply .... > ... </rpc_reply>
    mainContents = dom.getroot()
    # alright, lets get all the important data with the following recursion
    parsed = self.__getChildren(mainContents, self.RPC_NAMESPACE)
    self.__rpc_reply_formatted = parsed
    return self.__rpc_reply_formatted

  def __enter__ (self):
    """
    Context manager setup action.

    Usage::

      with AbstractNETCONFAdapter() as adapter:
        ...
    """
    if not self.connected:
      self.connect()
    return self

  def __exit__ (self, exc_type, exc_val, exc_tb):
    """
    Context manager cleanup action
    """
    if self.connected:
      self.disconnect()


class VNFRemoteManager(AbstractNETCONFAdapter):
  """
  This class is devoted to provide netconf specific callback functions and
  covering the background of how the netconf agent and the client work
  """
  # RPC namespace
  RPC_NAMESPACE = u'http://csikor.tmit.bme.hu/netconf/unify/vnf_starter'

  def __init__ (self, **kwargs):
    super(VNFRemoteManager, self).__init__(**kwargs)


if __name__ == "__main__":
  # TEST
  # print "Create VNFRemoteManager..."
  # vrm = VNFRemoteManager(server='192.168.12.128', port=830,
  # username='mininet', password='mininet', debug=True)
  # print "-" * 60
  # print "VNFRemoteManager:"
  # pprint(vrm.__dict__)
  print "-" * 60
  print "Connecting..."
  # vrm.connect()
  with VNFRemoteManager(server='192.168.12.128', port=830, username='mininet',
                        password='mininet', debug=True) as vrm:
    print "Connected"
    print "-" * 60
    print "Get config"
    print vrm.get_config()
    print "-" * 60
    print "Get /proc/meminfo..."
    # get /proc/meminfo
    print vrm.get()
    # call rpc getVNFInfo
    print "-" * 60
    print "Call getVNFInfo..."
    reply = vrm.rpc('getVNFInfo')
    print "-" * 60
    print "Reply:"
    pprint(reply)
    print "-" * 60
    print "Call initiateVNF..."
    reply = vrm.rpc("initiateVNF", vnf_type="headerDecompressor",
                    options={"ip": "127.0.0.1"})
    print "-" * 60
    print "Reply:"
    pprint(reply)
    print "-" * 60
    # print "Call connectVNF..."
    # reply = vrm.rpc("connectVNF", vnf_id='1', vnf_port="0", switch_id="s3")
    # print "-" * 60
    # print "Reply:"
    # pprint(reply)
    # print "-" * 60
    print "Call stopVNF..."
    reply = vrm.rpc("stopVNF", vnf_id='1')
    print "-" * 60
    print "Reply:"
    pprint(reply)
    print "-" * 60
    print "Disconnecting..."
    # vrm.disconnect()