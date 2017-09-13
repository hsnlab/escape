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
from os.path import abspath as abspath
from os.path import dirname as dirname

sys.path.append(abspath(dirname(__file__) + "/../unify_virtualizer"))
from virtualizer import Virtualizer

if __name__ == "__main__":
  parser = argparse.ArgumentParser(
    description="Convert ESCAPE's config file from JSON into YAML format.",
    add_help=True)
  parser.add_argument("old", type=str, help="old XML")
  parser.add_argument("new", type=str, help="new XML")
  args = parser.parse_args()
  old_virtualizer = Virtualizer.parse_from_file(filename=args.old)
  new_virtualizer = Virtualizer.parse_from_file(filename=args.new)
  print old_virtualizer.diff(target=new_virtualizer).xml()
