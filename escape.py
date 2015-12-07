#!/usr/bin/env python
#
# Copyright 2015 Janos Czentye <czentye@tmit.bme.hu>
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
Top starter script of ESCAPEv2 for convenient purposes
"""
import argparse
import os


def main ():
  # Implement parser options
  parser = argparse.ArgumentParser(
    description="ESCAPEv2: Extensible Service ChAin Prototyping Environment "
                "using Mininet, Click, NETCONF and POX",
    add_help=True,
    version="2.0.0")
  # Optional arguments
  escape = parser.add_argument_group("ESCAPEv2 arguments")
  escape.add_argument("-a", "--agent", action="store_true", default=False,
                      help="run in agent mode: start the ROS REST-API ("
                           "without the Service sublayer (SAS))")
  escape.add_argument("-c", "--config", metavar="path", type=str,
                      # default="pox/escape.config",
                      help="override default config filename")
  escape.add_argument("-d", "--debug", action="store_true", default=False,
                      help="run the ESCAPE in debug mode")
  escape.add_argument("-e", "--environment", action="store_true", default=False,
                      help="run ESCAPEv2 in the pre-defined virtualenv")
  escape.add_argument("-f", "--full", action="store_true", default=False,
                      help="run the infrastructure layer also")
  escape.add_argument("-i", "--interactive", action="store_true", default=False,
                      help="run an interactive shell for observing internal "
                           "states")
  escape.add_argument("-r", "--rosapi", action="store_true", default=False,
                      help="start the REST-API for the Resource Orchestration "
                           "sublayer (ROS)")
  escape.add_argument("-s", "--service", metavar="file", type=str,
                      help="skip the SAS REST-API initiation and read the "
                           "service request from the given file")
  escape.add_argument("-t", "--topo", metavar="file", type=str,
                      help="read the topology from the given file explicitly")
  escape.add_argument("-x", "--clean", action="store_true", default=False,
                      help="run the cleanup task standalone and kill remained "
                           "programs, interfaces, veth parts and junk files")
  escape.add_argument("-4", "--cfor", action="store_true", default=False,
                      help="start the REST-API for the Cf-Or interface")
  # Remaining arguments
  escape.add_argument("modules", metavar="...", nargs=argparse.REMAINDER,
                      help="optional POX modules")
  # Parsing arguments
  args = parser.parse_args()

  if args.clean:
    # Tailor Python path for importing mics functions without initialize
    # escape or util packages.
    import sys
    mn = os.path.abspath(os.path.dirname(__file__) + "/mininet")
    misc = os.path.abspath(os.path.dirname(__file__) + "/pox/ext/escape/util")
    sys.path.append(mn)
    sys.path.append(misc)
    if os.geteuid() != 0:
      print "Cleanup process requires root privilege!"
      return
    else:
      print "Run cleaning process..."
      from misc import remove_junks
      remove_junks()
      print "Cleaned."
      return

  # Get base dir of this script
  base_dir = os.path.abspath(os.path.dirname(__file__))

  # Create absolute path for the pox.py initial script
  cmd = os.path.join(base_dir, "pox/pox.py")

  # Construct POX init command according to argument
  # basic command
  cmd = "%s unify" % cmd

  # Run the Infrastructure Layer with the required root privilege
  if args.full:
    cmd = "sudo %s --full" % cmd

  # Read the service request NFFG from a file and start the mapping process
  if args.service:
    cmd = "%s --sg_file=%s" % (cmd, os.path.abspath(args.service))

  # Override optional external config file
  if args.config:
    cmd = "%s --config=%s" % (cmd, os.path.abspath(args.config))

  # Skip the Service Layer initiation and start the ROS agent REST-API
  if args.agent:
    cmd = "%s --agent" % cmd

  # Start the REST-API for the ROS layer
  if args.rosapi:
    cmd = "%s --rosapi" % cmd

  # Start an REST-API for the Cf-Or interface
  if args.cfor:
    cmd = "%s --cfor" % cmd
  if args.debug:
    # Nothing to do
    pass
  else:
    # Disable debug mode in normal mode
    cmd = "%s --debug=False" % cmd

  # Add topology file if --full is set
  if args.topo:
    if args.full:
      cmd = "%s --topo=%s" % (cmd, os.path.abspath(args.topo))
    else:
      parser.error(message="-t/--topo can be used only with -f/--full!")

  # Add the interactive shell if needed
  if args.interactive:
    cmd = "%s py --completion" % cmd

  # Add optional POX modules
  cmd = "%s %s" % (cmd, " ".join(args.modules))

  def __activate_virtualenv ():
    """
    Activate virtualenv based on activate script under bin/

    :return: None
    """
    try:
      activate_this = os.path.join(base_dir, 'bin/activate_this.py')
      execfile(activate_this, dict(__file__=activate_this))
    except IOError as e:
      print "Virtualenv is not set properly:\n%s" % e
      print "Remove the '.set_virtualenv' file or configure the virtualenv!"
      os._exit(1)

  # Activate virtual environment if necessary
  if args.environment:
    __activate_virtualenv()
  else:
    for entry in os.listdir(base_dir):
      if entry.upper().startswith(".USE_VIRTUALENV"):
        __activate_virtualenv()
        break

  # Starting ESCAPEv2 (as a POX module)
  print "Starting ESCAPEv2..."
  if args.debug:
    print "Command: %s" % cmd
  os.system(cmd)


if __name__ == '__main__':
  main()
