# Copyright 2017 Janos Czentye
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
import ast
import logging

import re

log = logging.getLogger("virt_helper")
NF_PATH_TEMPLATE = "/virtualizer/nodes/node[id=%s]/NF_instances/node[id=%s]"
# Use ? modifier after .* to define a non-greedy matching and skip ports
NODE_NF_PATTERN = r'.*nodes/node\[id=(.*?)\]/NF_instances/node\[id=(.*?)\]'


def get_nf_from_path (path):
  """
  Return the NF id from a Virtualizer path.

  :param path: path
  :type path: str
  :return: extracted NF name
  :rtype: str
  """
  mapping_regex = re.compile(NODE_NF_PATTERN)
  match = mapping_regex.match(path)
  if match is None:
    log.warning("Wrong object format: %s" % path)
    return
  return mapping_regex.match(path).group(2)


def get_bb_nf_from_path (path):
  """
  Return the BiSBiS node and NF id from a Virtualizer path.

  :param path: path
  :type path: str
  :return: extracted BB and NF name
  :rtype: tuple
  """
  mapping_regex = re.compile(NODE_NF_PATTERN)
  match = mapping_regex.match(path)
  if match is None:
    log.warning("Wrong object format: %s" % path)
    return
  return mapping_regex.match(path).group(1, 2)


def detect_bb_nf_from_path (path, topo):
  """
  Return the existing BiSBis and NF id referred by given path from topology.

  :param path: path
  :type path: str
  :param topo: topology object
  :type topo: :class:`NFFG`
  :return: extracted NF name
  :rtype: tuple
  """
  bb, nf = get_bb_nf_from_path(path=path)
  if bb not in topo or nf not in topo:
    log.warning("Missing requested element: %s on %s from topo!" % (nf, bb))
    return None, None
  log.debug("Detected NF: %s on %s" % (nf, bb))
  return bb, nf


def get_nfs_from_info (info):
  """
  Return NF IDs defined in Info request.

  :param info: Info object
  :type info: :class:`Info`
  :return: Nf Ids
  :rtype: set
  """
  nfs = set()
  log.debug("Extract NFs from info request...")
  for attr in (getattr(info, e) for e in info._sorted_children):
    for element in attr:
      if hasattr(element, "object"):
        nf = get_nf_from_path(element.object.get_value())
        if nf is not None:
          nfs.add(nf)
        else:
          log.warning("Missing NF from element:\n%s" % element.object.xml())
      else:
        log.warning("Missing 'object' from element:\n%s" % element.xml())
  return nfs


def strip_info_by_nfs (info, nfs):
  """
  Remove Info element from given Info structure where the referred NF is not
  in given nfs collection.

  :param info: Info object
  :type info: :class:`Info`
  :param nfs: collection of NF IDs
  :type nfs: list or set
  :return: stripped Info object
  :rtype: :class:`Info`
  """
  info = info.yang_copy()
  for attr in (getattr(info, e) for e in info._sorted_children):
    deletable = []
    for element in attr:
      if hasattr(element, "object"):
        nf_id = get_nf_from_path(element.object.get_value())
        if nf_id not in nfs:
          deletable.append(element)
    for d in deletable:
      attr.remove(d)
  return info


def is_empty (virtualizer, skipped=('version', 'id')):
  """
  Return True if the given Virtualizer object has no important child element.

  :param virtualizer: virtualizer object
  :type virtualizer: :class:`Virtualizer`
  :param skipped: non-significant child name
  :type skipped: tuple or list
  :return: is empty
  :rtype: bool
  """
  next_child = virtualizer.get_next()
  while next_child is not None:
    # Skip version tag (old format) and id (new format)
    if next_child.get_tag() not in skipped:
      return False
    else:
      next_child = next_child.get_next()
  return True


def is_identical (base, new):
  """
  Return True if the base and new Virtualizer object is identical.

  :param base: first Virtualizer object
  :type base: :class:`Virtualizer`
  :param new: first Virtualizer object
  :type new: :class:`Virtualizer`
  :return: is identical
  :rtype: bool
  """
  return is_empty(virtualizer=base.diff(new))


def _res_parser (raw_str):
  try:
    digits = filter(lambda c: c.isdigit() or c == '.', raw_str)
    return ast.literal_eval(digits)
  except SyntaxError:
    pass
