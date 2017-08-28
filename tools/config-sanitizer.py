#!/usr/bin/env python
# Copyright 2017 Janos Czentye <czentye@tmit.bme.hu>
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
import argparse
import sys
from collections import OrderedDict

import yaml
from yaml.resolver import BaseResolver


class OrderedYAMLLoader(yaml.SafeLoader):
  """
  Loader class which keeps order of mapping node elements
  """

  def __init__ (self, *args, **kwargs):
    super(OrderedYAMLLoader, self).__init__(*args, **kwargs)
    self.add_constructor(BaseResolver.DEFAULT_MAPPING_TAG,
                         self.__construct_ordered_mapping)

  @staticmethod
  def __construct_ordered_mapping (loader, node):
    loader.flatten_mapping(node)
    return OrderedDict(loader.construct_pairs(node))

  @classmethod
  def load (cls, stream):
    return yaml.load(stream, cls)


class OrderedYAMLDumper(yaml.SafeDumper):
  """
  Dumper class which handles OrderedDict mapping elements
  """

  def __init__ (self, *args, **kwargs):
    super(OrderedYAMLDumper, self).__init__(*args, **kwargs)
    self.add_representer(OrderedDict, self.__ordered_dict_representer)

  @staticmethod
  def __ordered_dict_representer (dumper, data):
    return dumper.represent_mapping(BaseResolver.DEFAULT_MAPPING_TAG,
                                    data.items())

  @classmethod
  def dump_data (cls, data, stream=None, **kwargs):
    return yaml.dump(data=data, stream=stream, Dumper=cls, **kwargs)


def main (file_name):
  with open(file_name) as istream:
    output_file = file_name.rsplit('.', 1)[0] + '.yaml'
    with open(output_file, 'w') as ostream:
      OrderedYAMLDumper.dump_data(data=OrderedYAMLLoader.load(istream),
                                  stream=ostream,
                                  default_flow_style=False,
                                  indent=4)


if __name__ == "__main__":
  if len(sys.argv) < 2:
    print "Missing argument: %s [file name]" % sys.argv[0]
    sys.exit(1)
  parser = argparse.ArgumentParser(
    description="Convert ESCAPE's config file from JSON into YAML format.",
    add_help=True)
  parser.add_argument("file", type=str, help="config file name")
  args = parser.parse_args()
  main(file_name=args.file)
