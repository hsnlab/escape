# Copyright 2015 Janos Czentye, Raphael Vicente Rosa
#
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
Contains helper classes for conversion between different NF-FG representations.
"""
import sys
import xml.etree.ElementTree as ET

try:
  # Import for ESCAPEv2
  from escape.util.nffg import AbstractNFFG, NFFG
except ImportError:
  import os, inspect

  sys.path.insert(0, os.path.join(os.path.abspath(
     os.path.join(os.path.dirname(__file__), "../../../..")),
     "pox/ext/escape/util/"))
  # Import for standalone running
  from nffg import AbstractNFFG, NFFG

try:
  # Import for ESCAPEv2
  import virtualizer3 as virt3
  from virtualizer3 import Flowentry
except ImportError:
  import os, inspect

  sys.path.insert(0, os.path.join(os.path.abspath(
     os.path.join(os.path.dirname(__file__), "../../../..")),
     "unify_virtualizer"))
  # Import for standalone running
  import virtualizer3 as virt3
  from virtualizer3 import Flowentry


class NFFGConverter(object):
  """
  Convert different representation of NFFG in both ways.
  """
  # port types in Virtualizer
  TYPE_VIRTUALIZER_PORT_ABSTRACT = "port-abstract"
  TYPE_VIRTUALIZER_PORT_SAP = "port-sap"
  # General option names in mapped NFFG assembled by the Mapping algorithm
  OPERATION_TAG = 'TAG'
  OPERATION_UNTAG = 'UNTAG'
  GENERAL_OPERATIONS = (OPERATION_TAG, OPERATION_UNTAG)
  # Operation formats in Virtualizer
  MATCH_VLAN_TAG = r"dl_vlan"
  ACTION_PUSH_VLAN = r"push_vlan"
  ACTION_STRIP_VLAN = r"strip_vlan"

  def __init__ (self, domain, logger=None):
    self.domain = domain
    self.log = logger if logger is not None else logging.getLogger(__name__)

  def parse_from_Virtualizer3 (self, xml_data, with_virt=False):
    """
    Convert Virtualizer3-based XML str --> NFFGModel based NFFG object

    :param xml_data: XML plain data formatted with Virtualizer
    :type: xml_data: str
    :param with_virt: return with the virtualizer too (default: False)
    :type with_virt: bool
    :return: created NF-FG
    :rtype: :any:`NFFG`
    """
    self.log.debug(
       "START conversion: Virtualizer(ver: %s) --> NFFG(ver: %s)" % (
         3, NFFG.version))
    try:
      self.log.debug("Converting data to graph-based NFFG structure...")
      # Parse given str to XML structure
      tree = ET.ElementTree(ET.fromstring(xml_data))
      # Parse Virtualizer structure
      self.log.debug("Parsing XML data to Virtualizer format...")
      virtualizer = virt3.Virtualizer().parse(root=tree.getroot())
    except ET.ParseError as e:
      raise RuntimeError('ParseError: %s' % e.message)

    # Get NFFG init params
    nffg_id = virtualizer.id.get_value() if virtualizer.id.is_initialized() \
      else "NFFG-%s" % self.domain
    nffg_name = virtualizer.name.get_value() if \
      virtualizer.name.is_initialized() else nffg_id

    self.log.debug("Construct NFFG based on Virtualizer(id=%s, name=%s)" % (
      nffg_id, nffg_name))
    # Create NFFG
    nffg = NFFG(id=nffg_id, name=nffg_name)

    # Iterate over virtualizer/nodes --> node = Infra
    for inode in virtualizer.nodes:
      # Node params
      node_id = inode.id.get_value()
      _name = inode.name.get_value() if inode.name.is_initialized() else \
        "name-" + node_id
      # Set domain as the domain of the Converter
      _domain = self.domain
      _infra_type = inode.type.get_value()
      # Node-resources params
      if inode.resources.is_initialized():
        # Remove units and store the value only
        _cpu = inode.resources.cpu.get_as_text().split(' ')[0]
        _mem = inode.resources.mem.get_as_text().split(' ')[0]
        _storage = inode.resources.storage.get_as_text().split(' ')[0]
        try:
          _cpu = int(_cpu)
          _mem = int(_mem)
          _storage = int(_storage)
        except ValueError as e:
          self.log.warning("Resource value is not valid number: %s" % e)
      else:
        # _cpu = sys.maxint
        # _mem = sys.maxint
        # _storage = sys.maxint
        _cpu = None
        _mem = None
        _storage = None

      # Iterate over links to summarize bw value for infra node
      # Default value: None
      _bandwidth = [
        float(link.resources.bandwidth.get_value()) for link in inode.links if
        link.resources.is_initialized() and
        link.resources.bandwidth.is_initialized()]
      _bandwidth = min(_bandwidth) if _bandwidth else None
      # Iterate over links to summarize delay value for infra node
      # Default value: None
      _delay = [
        float(link.resources.delay.get_value()) for link in inode.links if
        link.resources.is_initialized() and
        link.resources.delay.is_initialized()]
      _delay = max(_delay) if _delay else None

      # Add Infra Node
      infra = nffg.add_infra(id=node_id, name=_name, domain=_domain,
                             infra_type=_infra_type, cpu=_cpu, mem=_mem,
                             storage=_storage, delay=_delay,
                             bandwidth=_bandwidth)
      self.log.debug("Create infra: %s" % infra)

      # Add supported types shrinked from the supported NF list
      for sup_nf in inode.capabilities.supported_NFs:
        infra.add_supported_type(sup_nf.type.get_value())

      # Define default bw,delay value for SAP<->Infra links
      _bandwidth = _delay = None

      # Add ports to Infra Node
      for port in inode.ports:
        # If it is a port connected to a SAP
        if port.port_type.get_value() == self.TYPE_VIRTUALIZER_PORT_SAP:
          # If inter-domain SAP id = <sap> tag
          if port.sap.is_initialized():
            # Use unique SAP tag as the id of the SAP
            s_id = port.sap.get_value()
          # Regular SAP
          else:
            # Use port name as the SAP.id if it is set else generate one
            s_id = port.name.get_value() if port.name.is_initialized() else \
              "SAP%s" % len([s for s in nffg.saps])
          try:
            sap_port_id = int(port.id.get_value())
          except ValueError:
            sap_port_id = port.id.get_value()
          # SAP.name will be the same as the SAP.id or generate one for backup
          s_name = port.name.get_value() if port.name.is_initialized() else \
            "name-" + s_id

          # Create SAP and Add port to SAP
          # SAP default port: sap-type port number
          sap = nffg.add_sap(id=s_id, name=s_name)
          self.log.debug("Create SAP: %s" % sap)
          sap_port = sap.add_port(id=sap_port_id)
          # Add port properties as metadata to SAP port
          if port.name.is_initialized():
            sap_port.add_property("name:%s" % port.name.get_value())
          if port.sap.is_initialized():
            sap_port.add_property("sap:%s" % port.sap.get_value())
            # sap_port.add_property("type:%s" % port.sap.get_value())
            self.log.debug("Add SAP port: %s" % sap_port)

          # Create and add the opposite Infra port
          try:
            infra_port_id = int(port.id.get_value())
          except ValueError:
            infra_port_id = port.id.get_value()
          infra_port = infra.add_port(id=infra_port_id)
          # Add port properties as metadata to Infra port too
          infra_port.add_property("name:%s" % port.name.get_value())
          # infra_port.add_property("port_type:%s" % port.port_type.get_value())
          if port.sap.is_initialized():
            infra_port.add_property("sap:%s" % port.sap.get_value())

          # Add infra port capabilities
          if port.capability.is_initialized():
            infra_port.add_property(
               "capability:%s" % port.capability.get_value())
          self.log.debug("Add port for SAP -> %s" % infra_port)

          # Add connection between infra - SAP
          # SAP-Infra is static link --> create link for both direction
          l1, l2 = nffg.add_undirected_link(port1=sap_port, port2=infra_port,
                                            delay=_delay, bandwidth=_bandwidth)
          self.log.debug("Add connection: %s" % l1)
          self.log.debug("Add connection: %s" % l2)

        # If it is not SAP port and probably connected to another infra
        elif port.port_type.get_value() == self.TYPE_VIRTUALIZER_PORT_ABSTRACT:
          # Add default port
          try:
            infra_port_id = int(port.id.get_value())
          except ValueError:
            infra_port_id = port.id.get_value()

          # Add port properties as metadata to Infra port
          infra_port = infra.add_port(id=infra_port_id)
          if port.name.is_initialized():
            infra_port.add_property("name:%s" % port.name.get_value())
          # If sap is set and port_type is port-abstract -> this port
          # connected  to an inter-domain SAP before -> save this metadata
          if port.sap.is_initialized():
            infra_port.add_property("sap:%s" % port.sap.get_value())
          if port.capability.is_initialized():
            infra_port.add_property(
               "capability:%s" % port.capability.get_value())
          self.log.debug("Add static %s" % infra_port)
        else:
          raise RuntimeError(
             "Unsupported port type: %s" % port.port_type.get_value())

      # Create NF instances
      for nf_inst in inode.NF_instances:
        # Get NF params
        nf_id = nf_inst.id.get_value()
        nf_name = nf_inst.name.get_value() if nf_inst.name.is_initialized() \
          else None
        nf_ftype = nf_inst.type.get_value() if nf_inst.type.is_initialized() \
          else None
        nf_dtype = None
        if nf_inst.resources.is_initialized():
          nf_cpu = nf_inst.resources.cpu.get_value()
          nf_mem = nf_inst.resources.mem.get_value()
          nf_storage = nf_inst.resources.storage.get_value()
        else:
          nf_cpu = nf_mem = nf_storage = None
        try:
          nf_cpu = int(nf_cpu) if nf_cpu is not None else None
          nf_mem = int(nf_mem) if nf_cpu is not None else None
          nf_storage = int(nf_storage) if nf_cpu is not None else None
        except ValueError as e:
          self.log.warning("Resource value is not valid number: %s" % e)

        # Create NodeNF
        nf = nffg.add_nf(id=nf_id, name=nf_name, func_type=nf_ftype,
                         dep_type=nf_dtype, cpu=nf_cpu, mem=nf_mem,
                         storage=nf_storage, delay=_delay, bandwidth=_bandwidth)
        self.log.debug("Create NF: %s" % nf)

        # Clear res values for VNF - Infra links
        _bandwidth = _delay = None
        # Create NF ports
        for nf_inst_port in nf_inst.ports:

          # Create and Add port
          nf_port = nf.add_port(id=nf_inst_port.id.get_value())

          # Add port properties as metadata to NF port
          if nf_inst_port.capability.is_initialized():
            nf_port.add_property(
               "capability:%s" % nf_inst_port.capability.get_value())
          if nf_inst_port.name.is_initialized():
            nf_port.add_property("name:%s" % nf_inst_port.name.get_value())
          # VNF port can not be a SAP port -> skip <port_type> saving
          # VNF port can not be a SAP port -> skip <sap> saving
          self.log.debug("Add NF port: %s" % nf_port)

          # Add connection between Infra - NF
          # Infra - NF port on Infra side is always a dynamically generated port
          # Get the smallest available port for the Infra Node
          # dyn_port = max(max({p.id for p in infra.ports}) + 1,
          #                 len(infra.ports))
          dyn_port = '|'.join((node_id, nf_id, nf_inst_port.id.get_as_text()))
          # Add Infra-side port
          infra_port = infra.add_port(id=dyn_port)
          self.log.debug("Add port for NF -> %s" % infra_port)

          # NF-Infra is dynamic link --> create special undirected link
          l1, l2 = nffg.add_undirected_link(port1=nf_port, port2=infra_port,
                                            bandwidth=_bandwidth, delay=_delay,
                                            dynamic=True)
          self.log.debug("Add dynamic connection: %s" % l1)
          self.log.debug("Add dynamic connection: %s" % l2)

      # Create Flowrules
      for flowentry in inode.flowtable:
        fe_id = flowentry.id.get_value()
        # e.g. in_port=1(;TAG=SAP1|comp|1)
        _port = flowentry.port.get_target()
        match = "in_port="
        # Check if src port is a VNF port --> create the tagged port name
        if "NF_instances" in flowentry.port.get_as_text():
          _src_nf = _port.get_parent().get_parent()
          _src_node = _src_nf.get_parent().get_parent()
          # match += '|'.join(
          #    {i.id.get_value() for i in (_src_node, _src_nf, _port)})
          match += '|'.join((_src_node.id.get_as_text(),
                             _src_nf.id.get_as_text(),
                             _port.id.get_as_text()))
        # Else just Infra port --> add only the port number
        else:
          match += _port.id.get_as_text()
        _out = flowentry.out.get_target()
        action = "output="
        # Check if dst port is a VNF port --> create the tagged port name
        if "NF_instances" in flowentry.out.get_as_text():
          _dst_nf = _out.get_parent().get_parent()
          _dst_node = _dst_nf.get_parent().get_parent()
          action += '|'.join((_dst_node.id.get_as_text(),
                              _dst_nf.id.get_as_text(),
                              _port.id.get_as_text()))
        # Else just Infra port --> add only the port number
        else:
          action += _out.id.get_as_text()

        # Check if there is a matching operation -> currently just TAG is used
        if flowentry.match.is_initialized() and flowentry.match.get_value():
          if flowentry.match.get_as_text().startswith(self.MATCH_VLAN_TAG):
            match += ";%s=" % self.OPERATION_TAG
            # if src or dst was a SAP: SAP.id == port.name
            # if scr or dst is a VNF port name of parent of port
            if _port.port_type.get_as_text() == self.TYPE_VIRTUALIZER_PORT_SAP:
              _src_name = _port.name.get_as_text()
            else:
              _src_name = _port.get_parent().get_parent().id.get_as_text()
            if _out.port_type.get_as_text() == self.TYPE_VIRTUALIZER_PORT_SAP:
              _dst_name = _out.name.get_as_text()
            else:
              _dst_name = _out.get_parent().get_parent().id.get_as_text()
            # e.g. <match>dl_tag=0x0004</match> --> in_port=1;TAG=SAP2|fwd|4
            # Convert from int/hex to int
            _tag = int(flowentry.match.get_as_text().split('=')[1], base=0)
            match += "|".join((str(_src_name), str(_dst_name), str(_tag)))
          else:
            self.log.warning(
               "Not recognizable match operation in:\n%s" % flowentry)
            continue

        # Check if there is an action operation
        if flowentry.action.is_initialized() and flowentry.action.get_value():
          if flowentry.action.get_as_text() == self.ACTION_STRIP_VLAN:
            # e.g. <action>strip_vlan</action> --> output=EE2|fwd|1;UNTAG
            action += ";%s" % self.OPERATION_UNTAG
          elif flowentry.action.get_as_text().startswith(self.ACTION_PUSH_VLAN):
            action += ";%s=" % self.OPERATION_TAG
            # tag: src element name | dst element name | tag
            # if src or dst was a SAP: SAP.id == port.name
            # if scr or dst is a VNF port name of parent of port
            if _port.port_type.get_as_text() == self.TYPE_VIRTUALIZER_PORT_SAP:
              _src_name = _port.name.get_as_text()
            else:
              _src_name = _port.get_parent().get_parent().id.get_as_text()
            if _out.port_type.get_as_text() == self.TYPE_VIRTUALIZER_PORT_SAP:
              _dst_name = _out.name.get_as_text()
            else:
              _dst_name = _out.get_parent().get_parent().id.get_as_text()
            # e.g. <action>push_tag:0x0003</action> -->
            # output=1;TAG=decomp|SAP2|3
            # Convert from int/hex to int
            _tag = int(flowentry.action.get_as_text().split(':')[1], base=0)
            action += "|".join((_src_name, _dst_name, str(_tag)))
          else:
            self.log.warning(
               "Not recognizable action operation in:\n%s" % flowentry)
            continue

        # Get the src (port where fr need to store) and dst port id
        try:
          port_id = int(_port.id.get_value())
        except ValueError:
          port_id = _port.id.get_value()

        # Get port from NFFG in which need to store the fr
        try:
          # If the port is an Infra port
          if "NF_instances" not in flowentry.port.get_as_text():
            port = nffg[node_id].ports[port_id]
          # If the port is a VNF port -> get the dynamic port in the Infra
          else:
            _vnf_id = _port.get_parent().get_parent().id.get_value()
            _dyn_port = [l.dst.id for vnf, infra, l in
                         nffg.network.edges_iter([_vnf_id], data=True) if
                         l.type == NFFG.TYPE_LINK_DYNAMIC and l.src.id ==
                         port_id]
            if len(_dyn_port) > 1:
              self.log.warning(
                 "Multiple dynamic link detected for NF(id: %s) Use first "
                 "link ..." % _vnf_id)
            elif len(_dyn_port) < 1:
              raise RuntimeError()
            # Get dynamic port from infra
            port = nffg[node_id].ports[_dyn_port[0]]
        except:
          self.log.warning(
             "Port: %s is not found in the NFFG from the flowrule:\n%s" % (
               port_id, flowentry))
          continue

        if flowentry.resources.is_initialized() and \
           flowentry.resources.bandwidth.is_initialized():
          _fr_bw = flowentry.resources.bandwidth.get_value()
        else:
          _fr_bw = None

        fr = port.add_flowrule(id=fe_id, match=match, action=action,
                               bandwidth=_fr_bw)
        self.log.debug("Add %s" % fr)

    # Add links connecting infras
    for link in virtualizer.links:
      src_port = link.src.get_target().id.get_value()
      src_node = link.src.get_target().get_parent().get_parent().id.get_value()
      dst_port = link.dst.get_target().id.get_value()
      dst_node = link.dst.get_target().get_parent().get_parent().id.get_value()
      try:
        src_port = int(src_port)
        dst_port = int(dst_port)
      except ValueError as e:
        self.log.warning("Port id is not a valid number: %s" % e)
      params = dict()
      params['p1p2id'] = link.id.get_value()
      params['p2p1id'] = link.id.get_as_text() + "-back"
      if link.resources.is_initialized():
        params['delay'] = float(link.resources.delay.get_value()) if \
          link.resources.delay.is_initialized() else None
        params['bandwidth'] = float(link.resources.bandwidth.get_value()) if \
          link.resources.bandwidth.is_initialized() else None
      l1, l2 = nffg.add_undirected_link(
         port1=nffg[src_node].ports[src_port],
         port2=nffg[dst_node].ports[dst_port],
         **params
      )
      self.log.debug("Add static connection: %s" % l1)
      self.log.debug("Add static connection: %s" % l2)
    self.log.debug(
       "END conversion: Virtualizer(ver: %s) --> NFFG(ver: %s)" % (
         3, NFFG.version))
    return (nffg, virtualizer) if with_virt else nffg

  def dump_to_Virtualizer3 (self, nffg):
    """
    Convert given :any:`NFFG` to Virtualizer3 format.

    :param nffg: topology description
    :type nffg: :any:`NFFG`
    :return: topology in Virtualizer3 format
    """
    self.log.debug(
       "START conversion: NFFG(ver: %s) --> Virtualizer(ver: %s)" % (
         NFFG.version, 3))
    self.log.debug("Converting data to XML-based Virtualizer structure...")
    # Create empty Virtualizer
    virt = virt3.Virtualizer(id=str(nffg.id), name=str(nffg.name))
    self.log.debug("Creating Virtualizer based on %s" % nffg)

    for infra in nffg.infras:
      self.log.debug("Converting %s" % infra)
      # Create infra node with basic params - nodes/node/{id,name,type}
      infra_node = virt3.Infra_node(id=str(infra.id), name=str(infra.name),
                                    type=str(infra.infra_type))

      # Add resources nodes/node/resources
      if infra.resources.cpu:
        infra_node.resources.cpu.set_value(str(infra.resources.cpu))
      if infra.resources.mem:
        infra_node.resources.mem.set_value(str(infra.resources.mem))
      if infra.resources.storage:
        infra_node.resources.storage.set_value(str(infra.resources.storage))

      # Add ports to infra
      for port in infra.ports:
        # Check if the port is a dynamic port : 23412423523445 or sap1|comp|1
        try:
          if not int(port.id) < 65536:
            # Dynamic port connected to a VNF - skip
            continue
        except ValueError:
          # port is not a number
          if '|' in str(port.id):
            continue
        _port = virt3.Port(id=str(port.id))
        # Detect Port properties
        if port.get_property("name"):
          _port.name.set_value(port.get_property("name"))
        if port.get_property("capability"):
          _port.capability.set_value(port.get_property("capability"))
        # If SAP property is exist: this port connected to a SAP
        if port.get_property("sap"):
          _port.sap.set_value(port.get_property("sap"))
        # Set default port-type to port-abstract
        # during SAP detection the SAP<->Node port-type will be overridden
        _port.port_type.set_value(self.TYPE_VIRTUALIZER_PORT_ABSTRACT)
        # port_type: port-abstract & sap: -    -->  regular port
        # port_type: port-abstract & sap: <SAP...>    -->  was connected to
        # an inter-domain port - set this data in Virtualizer
        infra_node.ports.add(_port)
        self.log.debug("Add static %s" % port)

      # Add minimalistic Node for supported NFs based on supported list of NFFG
      for sup in infra.supported:
        infra_node.capabilities.supported_NFs.add(
           virt3.Node(id=str(sup), type=str(sup)))

      # Add infra to virtualizer
      virt.nodes.add(infra_node)

      if infra.resources.delay is not None or infra.resources.bandwidth is \
         not None:
        # Define full-mesh intra-links for nodes to set bandwidth and delay
        # values
        from itertools import combinations
        # Detect the number of ports
        port_num = len(infra_node.ports.port._data)
        if port_num > 1:
          # There are valid port-pairs
          for port_pair in combinations(
             (p.id.get_value() for p in infra_node.ports), 2):
            # Create link
            _link = virt3.Link(
               src=infra_node.ports[port_pair[0]],
               dst=infra_node.ports[port_pair[1]],
               resources=virt3.Link_resource(
                  delay=str(
                     infra.resources.delay) if infra.resources.delay else None,
                  bandwidth=str(
                     infra.resources.bandwidth) if infra.resources.bandwidth
                  else None
               )
            )
            # Call bind to resolve src,dst references to workaround a bug
            _link.bind()
            infra_node.links.add(_link)
        elif port_num == 1:
          # Only one port in infra - create loop-edge
          _src = _dst = iter(infra_node.ports).next()
          _link = virt3.Link(
             src=_src,
             dst=_dst,
             resources=virt3.Link_resource(
                delay=str(
                   infra.resources.delay) if infra.resources.delay else None,
                bandwidth=str(
                   infra.resources.bandwidth) if infra.resources.bandwidth
                else None
             )
          )  # Call bind to resolve src,dst references to workaround a bug
          _link.bind()
          infra_node.links.add(_link)
        else:
          # No port in Infra - unusual but acceptable
          self.log.warning(
             "No port has been detected in %s. Can not store internal "
             "bandwidth/delay value!" % infra)

    # Rewrite SAP - Node ports to add SAP to Virtualizer
    for sap in nffg.saps:
      for s, n, link in nffg.network.edges_iter([sap.id], data=True):
        if link.type != NFFG.TYPE_LINK_STATIC:
          continue
        # Rewrite port-type to port-sap
        virt.nodes[n].ports[str(link.dst.id)].port_type.set_value(
           self.TYPE_VIRTUALIZER_PORT_SAP)
        # Add SAP.name as name to port or use sap.id
        if link.src.get_property("name"):
          _name = link.src.get_property("name")
        else:
          # Store SAP.id in the name attribute instead of SAP.name
          # SAP.id is more important
          # _name = str(sap.name) if sap.name else str(sap.id)
          _name = str(sap.id)
        virt.nodes[n].ports[str(link.dst.id)].name.set_value(_name)
        self.log.debug(
           "Convert SAP to port: %s in infra: %s" % (link.dst.id, n))
        # Check if the SAP is an inter-domain SAP
        if nffg[s].domain is not None:
          virt.nodes[n].ports[str(link.dst.id)].sap.set_value(s)
          self.log.debug(
             "Convert inter-domain SAP to port: %s in infra: %s" % (
               link.dst.id, n))

    # Add link to Virtualizer
    for link in nffg.links:
      if link.type != NFFG.TYPE_LINK_STATIC:
        continue
      # SAP - Infra links are not stored in Virtualizer format
      # Skip backward link conversion <-- Virtualizer links are bidirectional
      if link.src.node.type == NFFG.TYPE_SAP or \
            link.dst.node.type == NFFG.TYPE_SAP or link.backward is True:
        continue
      self.log.debug("Add link: Node: %s, port: %s <--> Node: %s, port: %s" % (
        link.src.node.id, link.src.id, link.dst.node.id, link.dst.id))
      _link = virt3.Link(
         id=str(link.id),
         src=virt.nodes[str(link.src.node.id)].ports[str(link.src.id)],
         dst=virt.nodes[str(link.dst.node.id)].ports[str(link.dst.id)],
         resources=virt3.Link_resource(
            delay=str(link.delay),
            bandwidth=str(link.bandwidth)
         )
      )
      # Call bind to resolve src,dst references to workaround a bug
      _link.bind()
      virt.links.add(_link)
    # Call our adaptation function to convert VNfs and Flowrules into
    # Virtualizer
    virt = self.adapt_mapping_into_Virtualizer(virtualizer=virt, nffg=nffg)
    # explicitly call bind to resolve relative paths for safety reason
    virt.bind()
    self.log.debug(
       "END conversion: NFFG(ver: %s) --> Virtualizer(ver: %s)" % (
         NFFG.version, 3))
    # Return with created Virtualizer
    return virt

  @staticmethod
  def unescape_output_hack (data):
    return data.replace("&lt;", "<").replace("&gt;", ">")

  def adapt_mapping_into_Virtualizer (self, virtualizer, nffg):
    """
    Install NFFG part or complete NFFG into given Virtualizer.

    :param virtualizer: Virtualizer object based on ETH's XML/Yang version.
    :param nffg: splitted NFFG (not necessarily in valid syntax)
    :return: modified Virtualizer object
    """
    self.log.debug(
       "START adapting modifications from %s into Virtualizer(id=%s, name=%s)"
       % (nffg, virtualizer.id.get_as_text(), virtualizer.name.get_as_text()))
    self.log.debug("Check up on mapped NFs...")
    # Check every infra Node
    for infra in nffg.infras:
      # Cache discovered NF to avoid multiple detection of NF which has more
      # than one port
      discovered_nfs = []
      # Check in infra is exist in the Virtualizer
      if str(infra.id) not in virtualizer.nodes.node.keys():
        self.log.warning(
           "InfraNode: %s is not in the Virtualizer! Skip related "
           "initiations..." % infra)
        continue
      # Check every outgoing edge
      for u, v, link in nffg.network.out_edges_iter([infra.id], data=True):
        # Observe only the NF neighbours
        if link.dst.node.type != NFFG.TYPE_NF:
          continue
        nf = link.dst.node
        # Skip already detected NFs
        if nf.id in discovered_nfs:
          continue
        # Check if the NF is exist in the InfraNode
        if str(v) not in virtualizer.nodes[str(u)].NF_instances.node.keys():
          self.log.debug("Found uninitiated NF: %s in mapped NFFG" % nf)
          # Convert Resources to str for XML conversion
          v_nf_cpu = str(
             nf.resources.cpu) if nf.resources.cpu is not None else None
          v_nf_mem = str(
             nf.resources.mem) if nf.resources.mem is not None else None
          v_nf_storage = str(
             nf.resources.storage) if nf.resources.storage is not None else \
            None
          # Create Node object for NF
          v_nf = virt3.Node(
             id=str(nf.id), name=str(nf.name),
             type=str(nf.functional_type),
             resources=virt3.Software_resource(
                cpu=v_nf_cpu,
                mem=v_nf_mem,
                storage=v_nf_storage))
          # Add NF to Infra object
          virtualizer.nodes[str(u)].NF_instances.add(v_nf)
          # Cache discovered NF
          discovered_nfs.append(nf.id)
          self.log.debug(
             "Add NF: %s to Infra node(id=%s, name=%s, type=%s)" % (
               nf, virtualizer.nodes[str(u)].id.get_as_text(),
               virtualizer.nodes[str(u)].name.get_as_text(),
               virtualizer.nodes[str(u)].type.get_as_text()))
          # Add NF ports
          for port in nffg[v].ports:
            self.log.debug(
               "Add Port: %s to NF node: %s" % (port, v_nf.id.get_as_text()))
            nf_port = virt3.Port(id=str(port.id), port_type="port-abstract")
            virtualizer.nodes[str(u)].NF_instances[str(v)].ports.add(nf_port)
        else:
          self.log.debug("%s is already exist in the Virtualizer(id=%s, "
                         "name=%s)" % (nf, virtualizer.id.get_as_text(),
                                       virtualizer.name.get_as_text()))
      # Add flowrules to Virtualizer
      fe_cntr = 0
      # traverse every port in the Infra node
      for port in infra.ports:
        # Check every flowrule
        for flowrule in port.flowrules:
          self.log.debug("Convert flowrule: %s" % flowrule)

          # Define metadata
          fe_id = "ESCAPE-flowentry" + str(fe_cntr)
          fe_cntr += 1
          fe_pri = str(100)

          # Check if match starts with in_port
          fe = flowrule.match.split(';')
          if fe[0].split('=')[0] != "in_port":
            self.log.warning(
               "Missing 'in_port' from match in %s. Skip flowrule "
               "conversion..." % flowrule)
            continue

          # Check if the src port is a physical or virtual port
          in_port = fe[0].split('=')[1]
          if str(port.id) in virtualizer.nodes[
            str(infra.id)].ports.port.keys():
            # Flowrule in_port is a phy port in Infra Node
            in_port = virtualizer.nodes[str(infra.id)].ports[str(port.id)]
            self.log.debug(
               "Identify in_port: %s in match as a physical port in the "
               "Virtualizer" % in_port.id.get_as_text())
          else:
            self.log.debug(
               "Identify in_port: %s in match as a dynamic port. Tracking "
               "associated NF port in the Virtualizer..." % in_port)
            # in_port is a dynamic port --> search for connected NF's port
            nf_port = [l.dst for u, v, l in
                       nffg.network.out_edges_iter([infra.id], data=True) if
                       l.type == NFFG.TYPE_LINK_DYNAMIC and str(
                          l.src.id) == in_port]
            # There should be only one link between infra and NF
            if len(nf_port) < 1:
              self.log.warning(
                 "NF port is not found for dynamic Infra port: %s defined in "
                 "match field! Skip flowrule conversion..." % in_port)
              continue
            nf_port = nf_port[0]
            in_port = virtualizer.nodes[str(infra.id)].NF_instances[
              str(nf_port.node.id)].ports[str(nf_port.id)]
            self.log.debug("Found associated NF port: node=%s, port=%s" % (
              in_port.get_parent().get_parent().id.get_as_text(),
              in_port.id.get_as_text()))

          # Process match field
          match = self.__convert_flowrule_match_unified(flowrule.match)

          # Check if action starts with outport
          fe = flowrule.action.split(';')
          if fe[0].split('=')[0] != "output":
            self.log.warning(
               "Missing 'output' from action in %s. Skip flowrule "
               "conversion..." % flowrule)
            continue

          # Check if the dst port is a physical or virtual port
          out_port = fe[0].split('=')[1]
          if str(out_port) in virtualizer.nodes[
            str(infra.id)].ports.port.keys():
            # Flowrule output is a phy port in Infra Node
            out_port = virtualizer.nodes[str(infra.id)].ports[str(out_port)]
            self.log.debug(
               "Identify outport: %s in action as a physical port in the "
               "Virtualizer" % out_port.id.get_as_text())
          else:
            self.log.debug(
               "Identify outport: %s in action as a dynamic port. Track "
               "associated NF port in the Virtualizer..." % out_port)
            # out_port is a dynamic port --> search for connected NF's port
            nf_port = [l.dst for u, v, l in
                       nffg.network.out_edges_iter([infra.id], data=True) if
                       l.type == NFFG.TYPE_LINK_DYNAMIC and str(
                          l.src.id) == out_port]
            if len(nf_port) < 1:
              self.log.warning(
                 "NF port is not found for dynamic Infra port: %s defined in "
                 "action field! Skip flowrule conversion..." % out_port)
              continue
            nf_port = nf_port[0]
            out_port = virtualizer.nodes[str(infra.id)].NF_instances[
              str(nf_port.node.id)].ports[str(nf_port.id)]
            self.log.debug("Found associated NF port: node=%s, port=%s" % (
              # out_port.parent.parent.parent.id.get_as_text(),
              out_port.get_parent().get_parent().id.get_as_text(),
              out_port.id.get_as_text()))

          # Process action field
          action = self.__convert_flowrule_action_unified(flowrule.action)

          # Add Flowentry with converted params
          virt_fe = Flowentry(id=fe_id, priority=fe_pri, port=in_port,
                              match=match, action=action, out=out_port,
                              resources=virt3.Link_resource(
                                 bandwidth=str(flowrule.bandwidth)
                              ))
          # virt_fe.bind()
          self.log.debug("Generated Flowentry:\n%s" % virtualizer.nodes[
            infra.id].flowtable.add(virt_fe))
    # explicitly call bind to resolve relative paths for safety reason
    virtualizer.bind()
    self.log.debug(
       "END adapting modifications from %s into Virtualizer(id=%s, name=%s)"
       % (nffg, virtualizer.id.get_as_text(), virtualizer.name.get_as_text()))
    # Return with modified Virtualizer
    return virtualizer

  def __convert_flowrule_match (self, domain, match):
    """
    Convert Flowrule match field from NFFG format to Virtualizer according to
    domain.

    :param match: flowrule match field
    :type match: str
    :return: converted data
    :rtype: str
    """
    # E.g.:  "match": "in_port=1;TAG=SAP1|comp|1"
    if len(match.split(';')) < 2:
      return

    op = match.split(';')[1].split('=')
    if op[0] not in ('TAG',):
      self.log.warning("Unsupported match operand: %s" % op[0])
      return

    if domain == "OPENSTACK":
      if op[0] == "TAG":
        # E.g.: <match>dl_vlan=0x0037</match>
        try:
          vlan = int(op[1].split('|')[-1])
          return r"dl_vlan=%s" % format(vlan, '#06x')
        except ValueError:
          self.log.warning(
             "Wrong VLAN format: %s! Skip flowrule conversion..." % op[1])
          return

    elif domain == "UN":
      if op[0] == "TAG":
        # E.g.: <match><vlan_id>55</vlan_id></match>
        try:
          vlan = int(op[1].split('|')[-1])
        except ValueError:
          self.log.warning(
             "Wrong VLAN format: %s! Skip flowrule conversion..." % op[1])
          return
        xml = ET.Element('match')
        vlan_id = ET.SubElement(xml, 'vlan_id')
        vlan_id.text = str(vlan)
        return xml

  def __convert_flowrule_action (self, domain, action):
    """
    Convert Flowrule action field from NFFG format to Virtualizer according
    to domain.

    :param domain: domain name
    :param action: flowrule action field
    :return: converted data
    """
    # E.g.:  "action": "output=2;UNTAG"
    if len(action.split(';')) < 2:
      return

    op = action.split(';')[1].split('=')
    if op[0] not in ('TAG', 'UNTAG'):
      self.log.warning("Unsupported action operand: %s" % op[0])
      return

    if domain == "OPENSTACK":
      if op[0] == "TAG":
        # E.g.: <action>push_vlan:0x8100,set_field:0x0037</action>
        try:
          vlan = int(op[1].split('|')[-1])
          # return r"push_vlan:0x8100,set_field:%s" % format(vlan, '#06x')
          return r"mod_vlan_vid:%s" % format(vlan, '#06x')
        except ValueError:
          self.log.warning(
             "Wrong VLAN format: %s! Skip flowrule conversion..." % op[1])
          return

      elif op[0] == "UNTAG":
        # E.g.: <action>strip_vlan</action>
        return r"strip_vlan"

    elif domain == "UN":
      if op[0] == "TAG":
        # E.g.: <action><vlan><push>55<push/></vlan></action>
        try:
          vlan = int(op[1].split('|')[-1])
        except ValueError:
          self.log.warning(
             "Wrong VLAN format: %s! Skip flowrule conversion..." % op[1])
          return
        xml = ET.Element('action')
        push = ET.SubElement(ET.SubElement(xml, 'vlan'), "push")
        push.text = str(vlan)
        return xml

      elif op[0] == "UNTAG":
        # E.g.: <action><vlan><pop/></vlan></action>
        xml = ET.Element('action')
        ET.SubElement(ET.SubElement(xml, 'vlan'), "pop")
        return xml

  def __convert_flowrule_match_unified (self, match):
    """
    Convert Flowrule match field from NFFG format to a unified format used by
    the Virtualizer.

    Based on Open vSwitch syntax:
    http://openvswitch.org/support/dist-docs/ovs-ofctl.8.txt

    :param match: flowrule match field
    :type match: str
    :return: converted data
    :rtype: str
    """
    # E.g.:  "match": "in_port=1;TAG=SAP1|comp|1" -->
    # E.g.:  "match": "in_port=SAP2|fwd|1;TAG=SAP1|comp|1" -->
    # <match>(in_port=1)dl_tag=1</match>
    match_part = match.split(';')
    if len(match_part) < 2:
      if not match_part[0].startswith("in_port"):
        self.log.warning("Unrecognizable match field: %s" % match)
      return

    op = match_part[1].split('=')
    if op[0] not in self.GENERAL_OPERATIONS:
      self.log.warning("Unsupported match operand: %s" % op[0])
      return

    if op[0] == self.OPERATION_TAG:
      try:
        vlan_tag = int(op[1].split('|')[-1])
        return "%s=%s" % (self.MATCH_VLAN_TAG, format(vlan_tag, '#06x'))
      except ValueError:
        self.log.warning(
           "Wrong VLAN format: %s! Skip flowrule conversion..." % op[1])
        return

  def __convert_flowrule_action_unified (self, action):
    """
    Convert Flowrule action field from NFFG format to a unified format used by
    the Virtualizer.

    Based on Open vSwitch syntax:
    http://openvswitch.org/support/dist-docs/ovs-ofctl.8.txt

    :param action: flowrule action field
    :type action: str
    :return: converted data
    :rtype: str
    """
    # E.g.:  "action": "output=2;UNTAG"
    action_part = action.split(';')
    if len(action_part) < 2:
      if not action_part[0].startswith("output"):
        self.log.warning("Unrecognizable action field: %s" % action)
      return

    op = action_part[1].split('=')
    if op[0] not in self.GENERAL_OPERATIONS:
      self.log.warning("Unsupported action operand: %s" % op[0])
      return

    if op[0] == self.OPERATION_TAG:
      # E.g.: <action>push_tag:0x0037</action>
      try:
        vlan = int(op[1].split('|')[-1])
        return "%s:%s" % (self.ACTION_PUSH_VLAN, format(vlan, '#06x'))
      except ValueError:
        self.log.warning(
           "Wrong VLAN format: %s! Skip flowrule conversion..." % op[1])
        return
    elif op[0] == self.OPERATION_UNTAG:
      # E.g.: <action>strip_vlan</action>
      return self.ACTION_STRIP_VLAN


def test_xml_based_builder ():
  # builder = NFFGtoXMLBuilder()
  # infra = builder.add_infra()
  # port = builder.add_node_port(infra, NFFGtoXMLBuilder.PORT_ABSTRACT)
  # res = builder.add_node_resource(infra, "10 VCPU", "32 GB", "5 TB")
  # link = builder.add_inter_infra_link(port, port, delay="5ms",
  #                                     bandwidth="10Gbps")
  # nf_inst = builder.add_nf_instance(infra)
  # nf_port = builder.add_node_port(nf_inst,
  # NFFGtoXMLBuilder.PORT_ABSTRACT)
  # sup_nf = builder.add_supported_nf(infra)
  # res_sup = builder.add_node_resource(sup_nf, 10, 10, 10)
  # builder.add_node_port(sup_nf, NFFGtoXMLBuilder.PORT_ABSTRACT)
  # builder.add_flow_entry(infra, port, nf_port,
  #                        action="mod_dl_src=12:34:56:78:90:12", delay="5ms",
  #                        bandwidth="10Gbps")

  # Generate same output as Agent_http.py
  # builder = XMLBasedNFFGBuilder()
  # builder.id = "UUID-ETH-001"
  # builder.name = "ETH OpenStack-OpenDaylight domain"
  # infra = builder.add_infra(
  #   name="single Bis-Bis node representing the whole domain")
  # infra_port0 = builder.add_node_port(infra, name="OVS-north external port")
  # infra_port1 = builder.add_node_port(infra, name="OVS-south external port")
  # builder.add_node_resource(infra, cpu="10 VCPU", mem="32 GB", storage="5 TB")
  # nf1 = builder.add_nf_instance(infra, id="NF1", name="example NF")
  # nf1port0 = builder.add_node_port(nf1, name="Example NF input port")
  # nf1port1 = builder.add_node_port(nf1, name="Example NF output port")
  # sup_nf = builder.add_supported_nf(infra, id="nf_a",
  #                                   name="tcp header compressor")
  # builder.add_node_port(sup_nf, name="in", param="...")
  # builder.add_node_port(sup_nf, name="out", param="...")
  # builder.add_flow_entry(infra, in_port=infra_port0, out_port=nf1port0)
  # builder.add_flow_entry(infra, in_port=nf1port1, out_port=infra_port1,
  #                        action="mod_dl_src=12:34:56:78:90:12")
  # print builder
  pass


def test_topo_un ():
  topo = """
<virtualizer>
    <name>Single node</name>
    <nodes>
        <node>
            <NF_instances>
                <node>
                    <name>DPI NF</name>
                    <ports>
                        <port>
                            <name>NF input port</name>
                            <port_type>port-abstract</port_type>
                            <id>1</id>
                        </port>
                        <port>
                            <name>NF output port</name>
                            <port_type>port-abstract</port_type>
                            <id>2</id>
                        </port>
                    </ports>
                    <type>dpi</type>
                    <id>NF1</id>
                </node>
            </NF_instances>
            <flowtable>
                <flowentry>
                    <port>../../../ports/port[id=1]</port>
                    <priority>100</priority>
                    <action>
                        <vlan>
                            <pop/>
                        </vlan>
                    </action>
                    <id>1</id>
                    <match>
                        <vlan_id>2</vlan_id>
                    </match>
                    <out>../../../NF_instances/node[id=NF1]/ports/port[id=1]
                    </out>
                </flowentry>
                <flowentry>
                    <port>../../../NF_instances/node[id=NF1]/ports/port[id=2]
                    </port>
                    <action>
                        <vlan>
                            <push>3</push>
                        </vlan>
                    </action>
                    <id>2</id>
                    <out>../../../ports/port[id=1]</out>
                </flowentry>
            </flowtable>
            <capabilities>
                <supported_NFs>
                    <node>
                        <name>DPI based on libpcre</name>
                        <ports>
                            <port>
                                <name>VNF port 1</name>
                                <port_type>port-abstract</port_type>
                                <id>1</id>
                            </port>
                            <port>
                                <name>VNF port 2</name>
                                <port_type>port-abstract</port_type>
                                <id>2</id>
                            </port>
                        </ports>
                        <type>dpi</type>
                        <id>NF1</id>
                    </node>
                    <node>
                        <name>iptables based firewall</name>
                        <ports>
                            <port>
                                <name>VNF port 1</name>
                                <port_type>port-abstract</port_type>
                                <id>1</id>
                            </port>
                            <port>
                                <name>VNF port 2</name>
                                <port_type>port-abstract</port_type>
                                <id>2</id>
                            </port>
                        </ports>
                        <type>firewall</type>
                        <id>NF2</id>
                    </node>
                    <node>
                        <name>NAT based on iptables</name>
                        <ports>
                            <port>
                                <name>VNF port 1</name>
                                <port_type>port-abstract</port_type>
                                <id>1</id>
                            </port>
                            <port>
                                <name>VNF port 2</name>
                                <port_type>port-abstract</port_type>
                                <id>2</id>
                            </port>
                        </ports>
                        <type>nat</type>
                        <id>NF3</id>
                    </node>
                    <node>
                        <name>ntop monitor</name>
                        <ports>
                            <port>
                                <name>VNF port 1</name>
                                <port_type>port-abstract</port_type>
                                <id>1</id>
                            </port>
                            <port>
                                <name>VNF port 2</name>
                                <port_type>port-abstract</port_type>
                                <id>2</id>
                            </port>
                        </ports>
                        <type>monitor</type>
                        <id>NF4</id>
                    </node>
                    <node>
                        <name>example VNF with several implementations</name>
                        <ports>
                            <port>
                                <name>VNF port 1</name>
                                <port_type>port-abstract</port_type>
                                <id>1</id>
                            </port>
                            <port>
                                <name>VNF port 2</name>
                                <port_type>port-abstract</port_type>
                                <id>2</id>
                            </port>
                        </ports>
                        <type>example</type>
                        <id>NF5</id>
                    </node>
                </supported_NFs>
            </capabilities>
            <ports>
                <port>
                    <name>OVS-north external port</name>
                    <port_type>port-sap</port_type>
                    <id>1</id>
                    <sap>SAP34</sap>
                </port>
            </ports>
            <type>BisBis</type>
            <id>UUID11</id>
            <resources>
                <mem>32 GB</mem>
                <storage>5 TB</storage>
                <cpu>10 VCPU</cpu>
            </resources>
            <name>Universal Node</name>
        </node>
    </nodes>
    <id>UUID001</id>
</virtualizer>
  """
  return topo


def test_topo_os ():
  topo = """
<virtualizer>
    <name>ETH OpenStack-OpenDaylight domain with request</name>
    <nodes>
        <node>
            <NF_instances>
                <node>
                    <name>Parental control B.4</name>
                    <ports>
                        <port>
                            <name>in</name>
                            <capability>...</capability>
                            <port_type>port-abstract</port_type>
                            <id>NF1_in</id>
                        </port>
                    </ports>
                    <type>1</type>
                    <id>NF1</id>
                    <resources>
                        <mem>1024</mem>
                    </resources>
                </node>
            </NF_instances>
            <flowtable>
                <flowentry>
                    <port>../../../ports/port[id=0]</port>
                    <action>strip_vlan</action>
                    <id>f1</id>
                    <match>dl_vlan=1</match>
                    <out>
                        ../../../NF_instances/node[id=NF1]/ports/port[id=NF1_in]
                    </out>
                </flowentry>
                <flowentry>
                    <port>
                        ../../../NF_instances/node[id=NF1]/ports/port[id=NF1_in]
                    </port>
                    <action>mod_vlan_vid:2</action>
                    <id>f2</id>
                    <out>../../../ports/port[id=0]</out>
                </flowentry>
            </flowtable>
            <capabilities>
                <supported_NFs>
                    <node>
                        <name>image0</name>
                        <ports>
                            <port>
                                <name>input port</name>
                                <port_type>port-abstract</port_type>
                                <id>0</id>
                            </port>
                        </ports>
                        <type>0</type>
                        <id>NF0</id>
                    </node>
                    <node>
                        <name>image1</name>
                        <ports>
                            <port>
                                <name>input port</name>
                                <port_type>port-abstract</port_type>
                                <id>0</id>
                            </port>
                        </ports>
                        <type>1</type>
                        <id>NF1</id>
                        <resources>
                            <mem>1024</mem>
                        </resources>
                    </node>
                </supported_NFs>
            </capabilities>
            <ports>
                <port>
                    <name>OVS-north external port</name>
                    <port_type>port-sap</port_type>
                    <id>0</id>
                    <sap>SAP24</sap>
                </port>
            </ports>
            <type>BisBis</type>
            <id>UUID-01</id>
            <resources>
                <mem>32 GB</mem>
                <storage>5 TB</storage>
                <cpu>10 VCPU</cpu>
            </resources>
            <name>single Bis-Bis node representing the whole domain</name>
        </node>
    </nodes>
    <id>UUID-ETH-001-req1</id>
</virtualizer>
"""
  return topo


if __name__ == "__main__":
  import logging

  logging.basicConfig(level=logging.DEBUG)
  log = logging.getLogger(__name__)
  c = NFFGConverter(domain="OPENSTACK", logger=log)
  # nffg, vv = c.parse_from_Virtualizer3(xml_data=txt)
  # # UN
  # nffg.network.node['UUID11'].ports[1].add_flowrule(
  #   match="in_port=1;TAG=sap1-comp-42", action="output=2;UNTAG")
  # OS
  # nffg.network.node['UUID-01'].ports[1].add_flowrule(
  #   match="in_port=1;TAG=sap1-comp-42", action="output=0;UNTAG")
  # nffg.network.node['UUID-01'].ports[1].add_flowrule(
  #   match="in_port=1;TAG=sap1-comp-42", action="output=0;UNTAG")
  # from pprint import pprint
  #
  # pprint(nffg.network.__dict__)
  # print nffg.dump()

  # from nffg import gen
  #
  # nffg = gen()
  # print nffg.dump()
  # v = c.dump_to_Virtualizer3(nffg, virtualizer=vv)
  # v, nffg = c.dump_to_Virtualizer3(nffg)
  # out = str(v)
  # out = out.replace("&lt;", "<").replace("&gt;", ">")
  # print out

  # with open(
  #    "../../../../examples/escape-mn-topo.nffg") as f:
  #   nffg = NFFG.parse(raw_data=f.read())
  #   nffg.duplicate_static_links()
  # print "Parsed NFFG: %s" % nffg
  # virt = c.dump_to_Virtualizer3(nffg=nffg)
  # print "Converted:"
  # print virt.xml()
  # print "Reconvert to NFFG:"
  # nffg, v = c.parse_from_Virtualizer3(xml_data=virt.xml())
  # print nffg.dump()

  with open(
     "../../../../examples/escape-mn-dov.xml") as f:
    tree = tree = ET.ElementTree(ET.fromstring(f.read()))
    dov = virt3.Virtualizer().parse(root=tree.getroot())
  nffg = c.parse_from_Virtualizer3(xml_data=dov.xml())
  print nffg.dump()
