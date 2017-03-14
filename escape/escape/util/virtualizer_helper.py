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
import logging

import re

log = logging.getLogger("virt_helper")
NF_PATH_TEMPLATE = "/virtualizer/nodes/node[id=%s]/NF_instances/node[id=%s]"
# Use ? modifier after .* to define a non-greedy matching and skip ports
NODE_NF_PATTERN = r'.*nodes/node\[id=(.*?)\]/NF_instances/node\[id=(.*?)\]'


def get_nf_from_path (path):
  mapping_regex = re.compile(NODE_NF_PATTERN)
  match = mapping_regex.match(path)
  if match is None:
    log.warning("Wrong object format: %s" % path)
    return
  return mapping_regex.match(path).group(2)


def get_bb_nf_from_path (path):
  mapping_regex = re.compile(NODE_NF_PATTERN)
  match = mapping_regex.match(path)
  if match is None:
    log.warning("Wrong object format: %s" % path)
    return
  return mapping_regex.match(path).group(1, 2)


def detect_bb_nf_from_path (path, topo):
  bb, nf = get_bb_nf_from_path(path=path)
  if bb not in topo or nf not in topo:
    log.warning("Missing requested element: %s on %s from topo!" % (nf, bb))
    return None, None
  log.debug("Detected NF: %s on %s" % (nf, bb))
  return bb, nf


def get_nfs_from_info (info):
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
  info = info.full_copy()
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
