#!/usr/bin/env python
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
import hashlib
import pprint
from argparse import ArgumentParser

import yaml
from flask import Flask, request, Response
from flask_httpauth import HTTPBasicAuth

ESC_DEF_CFG = "escape-config.yaml"
DEFAULT_PORT = 8888

parser = ArgumentParser(description="Restart waiter",
                        add_help=True)
parser.add_argument("-c", "--config", default=ESC_DEF_CFG,
                    help="configuration for REST-API (default: %s)" %
                         ESC_DEF_CFG)
args, unknown = parser.parse_known_args()

CONFIG = {}

with open(ESC_DEF_CFG) as f:
  esc_cfg = yaml.safe_load(f)
  for key in ('host', 'port', 'auth_user', 'auth_secret', 'prefix'):
    CONFIG[key] = esc_cfg['REST-API'][key]

if args.config:
  with open(args.config) as f:
    esc_cfg = yaml.safe_load(f)
    for key in ('host', 'port', 'auth_user', 'auth_secret', 'prefix'):
      try:
        CONFIG[key] = esc_cfg['REST-API'][key]
      except KeyError:
        pass

print "Parsed configuration:"
pprint.pprint(CONFIG, indent=2)

app = Flask(__name__)
auth = HTTPBasicAuth()


@auth.hash_password
def hash_passwd (passwd):
  return hashlib.md5(passwd).hexdigest()


@auth.get_password
def get_passwd (username):
  if username == CONFIG['auth_user']:
    return CONFIG['auth_secret']
  print "Invalid username!"


@app.route("/%s/admin/start" % CONFIG['prefix'], methods=['GET', 'POST'])
@auth.login_required
def wait_for_exit ():
  print "Authenticated!"
  shutdown_func = request.environ.get('werkzeug.server.shutdown')
  if shutdown_func is None:
    raise RuntimeError('Not running with the Werkzeug Server')
  else:
    shutdown_func()
  return Response("START accepted.\n")


if __name__ == "__main__":
  try:
    print "Waiting for start command..."
    app.run(host=CONFIG['host'], port=CONFIG['port'])
  except KeyboardInterrupt:
    pass
  print "Exit"
