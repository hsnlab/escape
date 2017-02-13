#!/usr/bin/python -u
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
import imp
import os

MAIN_CONTAINER_LAYER_NAME = "ESCAPE"


def get_escape_version ():
  misc = imp.load_source("misc", os.path.join(os.path.abspath(
    os.path.dirname(__file__)), "escape/escape/util/misc.py"))
  return getattr(misc, "get_escape_version")()


def main ():
  # Implement parser options
  parser = argparse.ArgumentParser(
    description="ESCAPEv2: Extensible Service ChAin Prototyping Environment "
                "using Mininet, Click, NETCONF and POX",
    add_help=True,
    version=get_escape_version(),
    prefix_chars="-+")
  # Add optional arguments
  escape = parser.add_argument_group("ESCAPEv2 arguments")
  escape.add_argument("-a", "--agent", action="store_true", default=False,
                      help="run in AGENT mode: start the infrastructure layer "
                           "with the ROS REST-API (without the Service "
                           "sublayer (SAS))")
  escape.add_argument("-c", "--config", metavar="path", type=str,
                      # default="pox/escape.config",
                      help="override default config filename")
  escape.add_argument("-d", "--debug", action="count", default=0,
                      help="run the ESCAPE in debug mode (can use multiple "
                           "times for more verbose logging)")
  escape.add_argument("-e", "--environment", action="store_true", default=False,
                      help="run ESCAPEv2 in the pre-defined virtualenv")
  escape.add_argument("-f", "--full", action="store_true", default=False,
                      help="run the infrastructure layer also")
  escape.add_argument("-g", "--gui", action="store_true", default=False,
                      help="initiate the graph-viewer GUI app which "
                           "automatically connects to the ROS REST-API")
  escape.add_argument("-i", "--interactive", action="store_true", default=False,
                      help="run an interactive shell for observing internal "
                           "states")
  escape.add_argument("-l", "--log", metavar="file", type=str,
                      help="add log file explicitly for test mode "
                           "(default: log/escape.log)")
  escape.add_argument("-m", "--mininet", metavar="file", type=str,
                      help="read the Mininet topology from the given file")
  escape.add_argument("-p", "--POXlike", action="store_true", default=False,
                      help="start ESCAPEv2 in the actual interpreter using "
                           "./pox as working directory instead of using a "
                           "separate shell process with POX's own PYTHON env")
  escape.add_argument("-r", "--rosapi", action="store_true", default=False,
                      help="start the REST-API for the Resource Orchestration "
                           "sublayer (ROS)")
  escape.add_argument("-s", "--service", metavar="file", type=str,
                      help="skip the SAS REST-API initiation and read the "
                           "service request from the given file")
  escape.add_argument("-t", "--test", action="store_true", default=False,
                      help="run in test mode")
  escape.add_argument("-q", "--quit", action="store_true", default=False,
                      help="quit right after the first service request has "
                           "processed")
  escape.add_argument("+q", "++quit", action="store_false", default=False,
                      help="explicitly disable quit mode")
  escape.add_argument("-x", "--clean", action="store_true", default=False,
                      help="run the cleanup task standalone and kill remained "
                           "programs, interfaces, veth parts and junk files")
  escape.add_argument("-V", "--visualization", action="store_true",
                      default=False,
                      help="run the visualization module to send data to a "
                           "remote server")
  escape.add_argument("-4", "--cfor", action="store_true", default=False,
                      help="start the REST-API for the Cf-Or interface")
  # Add remaining POX modules
  escape.add_argument("modules", metavar="...", nargs=argparse.REMAINDER,
                      help="optional POX modules")
  # Parsing arguments
  args = parser.parse_args()
  if args.clean:
    # Tailor Python path for importing mics functions without initialize
    # escape or util packages.
    import sys
    # Import misc directly from util/ to avoid standard ESCAPE init steps
    sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + "/mininet"))
    sys.path.insert(0, os.path.abspath(
      os.path.dirname(__file__) + "/escape/escape/util"))
    if os.geteuid() != 0:
      print "Cleanup process requires root privilege!"
      return
    else:
      print "Run full cleaning process..."
      # Kill stacked ESCAPE processes
      from misc import run_cmd
      run_cmd('sudo -S pkill -f "%s"' % MAIN_CONTAINER_LAYER_NAME)
      from misc import remove_junks_at_shutdown, remove_junks_at_boot
      # Remove remained temporarily files
      remove_junks_at_shutdown()
      # Remove log files from /tmp
      remove_junks_at_boot()
      print "Cleaned."
      return

  # Get base dir of this script
  base_dir = os.path.abspath(os.path.dirname(__file__))

  # Create absolute path for the pox.py initial script
  # Construct POX init command according to argument
  # basic command
  cmd = [os.path.join(base_dir, "pox/pox.py"), MAIN_CONTAINER_LAYER_NAME]

  # Run ESCAPE in VERBOSE logging level if it is needed
  if args.debug == 1:
    # Set logging level to DEBUG
    cmd.append("--loglevel=DEBUG")
  elif args.debug > 1:
    # Setup logging level to specific VERBOSE
    cmd.append("--loglevel=VERBOSE")
  else:
    # Use default loglevel: INFO
    pass

  # Run the Infrastructure Layer with the required root privilege
  if args.full:
    cmd.insert(0, "sudo")
    cmd.append("--full")

  if args.test:
    cmd.append("--test")
  if args.log:
    cmd.append("--log=%s" % args.log)

  if args.quit:
    cmd.append("--quit")

  # Initiate the rudimentary GUI
  if args.gui:
    cmd.append("--gui")

  # Read the service request NFFG from a file and start the mapping process
  if args.service:
    cmd.append("--sg_file=%s" % os.path.abspath(args.service))

  # Override optional external config file
  if args.config:
    cmd.append("--config=%s" % os.path.abspath(args.config))

  # Skip the Service Layer initiation and start the ROS agent REST-API
  if args.agent:
    cmd.append("--agent")
    # AGENT mode is only useful with --full -> initiate infrastructure if needed
    if not args.full:
      cmd.insert(0, "sudo")
      cmd.append("--full")

  # Start the REST-API for the ROS layer
  if args.rosapi or args.gui:
    cmd.append("--rosapi")

  # Start an REST-API for the Cf-Or interface
  if args.cfor:
    cmd.append("--cfor")

  # Enable Visualization
  if args.visualization:
    cmd.append("--visualization")

  # Add topology file if --full is set
  if args.mininet:
    if args.full or args.agent:
      cmd.append("--mininet=%s" % os.path.abspath(args.mininet))
    else:
      parser.error(
        message="-m/--mininet can be used only with Infrastructure layer! "
                "(with -f/--full or -a/--agent flag)")

  # Add the interactive shell if needed
  if args.interactive:
    cmd.append("py")
    cmd.append("--completion")

  # Add optional POX modules
  cmd.extend(args.modules)

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
  print "Starting %s..." % parser.description

  if args.POXlike:
    pox_base = os.path.realpath((os.path.dirname(__file__) + "/pox"))
    # Change working directory
    os.chdir(pox_base)
    # Override first path element
    # POX use the first element of path to add pox directories to PYTHONPATH
    import sys
    sys.path[0] = pox_base
    pox_params = cmd[2:] if cmd[0] == "sudo" else cmd[1:]
    if args.debug:
      print "POX base: %s" % pox_base
      print "POX parameters: %s" % pox_params
    from pox.boot import boot
    boot(argv=pox_params)
  else:
    # Create command
    cmd = " ".join(cmd)
    if args.debug:
      print "Command: %s" % cmd
    os.system(cmd)


if __name__ == '__main__':
  main()
