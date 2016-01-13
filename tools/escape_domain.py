#!/usr/bin/env python

import logging
import os
import sys
import inspect

from tornado.web import RequestHandler
from tornado.web import Application, url
from tornado.ioloop import IOLoop

sys.path.insert(0, os.path.join(os.path.abspath(os.path.realpath(
  os.path.abspath(
    os.path.split(inspect.getfile(inspect.currentframe()))[0])) + "/.."),
                                "pox/ext/escape/util/"))
from nffg import NFFG

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)
LOG.propagate = False
sh = logging.StreamHandler()
sh.setLevel(logging.DEBUG)
f = logging.Formatter('%(asctime)s:%(name)s:%(levelname)s:%(message)s')
sh.setFormatter(f)
LOG.addHandler(sh)

CONFIG_FILE = 'escape-remote-topo.nffg'


class VirtualizationService(RequestHandler):
  # HTTP GET method on http://hostip:8080/rpc_name will trigger this function
  #  with rpc=rpc_name
  def get (self, rpc=None):

    if rpc == 'ping':
      LOG.debug('ping received')
      self.write('OK')
    else:
      self.write('usage:\n')
      self.write('get http://hostip:8083/virtualizer - this help message\n')
      self.write(
        'get http://hostip:8083/virtualizer/ping - test webserver aliveness\n')
      self.write(
        'post http://hostip:8083/virtualizer/ping - test webserver aliveness\n')
      self.write(
        'post http://hostip:8083/virtualizer/get-config - query nf-fg\n')
      self.write(
        'post http://hostip:8083/virtualizer/edit-config - send nf-fg request '
        'in the post body')

  # HTTP POST method on http://hostip:8080/rpc_name will trigger this
  # function with rpc=rpc_name
  def post (self, rpc=None):

    if rpc == 'ping':
      LOG.debug('ping received')
      self.write('OK')

    elif rpc == 'get-config':
      LOG.debug('get-config received')
      with open(CONFIG_FILE) as f:
        nffg = NFFG.parse(f.read())
        nffg.duplicate_static_links()
        self.write(nffg.dump())
      return

    elif rpc == 'edit-config':
      # parse body if it contains a Nf-fg:
      nffg = None
      if self.request.body:
        nffg = NFFG.parse(self.request.body)
      if nffg is None:
        self.send_error(400)
        return
      LOG.debug('edit-config received: %s', nffg.dump())
      return
    else:
      self.set_status(404)
      self.write_error(404)


def start ():
  LOG.debug('Start tornado server')
  app = Application([url(r"/(.*)", VirtualizationService)])
  app.listen(8083)
  IOLoop.current().start()


if __name__ == '__main__':
  try:
    start()
  except KeyboardInterrupt:
    pass
