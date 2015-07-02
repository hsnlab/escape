#!/usr/bin/env python
__author__ = 'Janos Elek'
__copyright__ = 'Copyright Ericsson Hungary Ltd 2015'

__maintainer__ = 'David Jocha'
__email__ = 'david.jocha@ericsson.com'

import logging

from tornado.web import RequestHandler
from tornado.web import Application, url
from tornado.ioloop import IOLoop

import nffglib

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)
LOG.propagate = False
sh = logging.StreamHandler()
sh.setLevel(logging.DEBUG)
f = logging.Formatter('%(asctime)s:%(name)s:%(levelname)s:%(message)s')
sh.setFormatter(f)
LOG.addHandler(sh)

CONFIG_FILE = 'infra_domain.xml'


class VirtualizationService(RequestHandler):
    # HTTP GET method on http://hostip:8080/rpc_name will trigger this function with rpc=rpc_name
    def get(self, rpc=None):

        if rpc == 'ping':
            LOG.debug('ping received')
            self.write('OK')
        else:
            self.write('usage:\n')
            self.write('get http://hostip:8888/virtualizer - this help message\n')
            self.write('get http://hostip:8888/virtualizer/ping - test webserver aliveness\n')
            self.write('post http://hostip:8888/virtualizer/ping - test webserver aliveness\n')
            self.write('post http://hostip:8888/virtualizer/get-config - query nf-fg\n')
            self.write('post http://hostip:8888/virtualizer/edit-config - send nf-fg request in the post body')

    # HTTP POST method on http://hostip:8080/rpc_name will trigger this function with rpc=rpc_name
    def post(self, rpc=None):

        if rpc == 'ping':
            LOG.debug('ping received')
            self.write('OK')

        elif rpc == 'get-config':
            LOG.debug('get-config received')
            xml_config = get_config()
            self.write(xml_config)
            return

        elif rpc == 'edit-config':

            # parse body if it contains a Nf-fg:
            nffg = None
            if self.request.body:
                try:
                    nffg = nffglib.Virtualizer.parse(text=self.request.body)
                except nffglib.InvalidXML as e:
                    LOG.debug('Error in parsing: %s', e.message)
                    message = 'Unable to parse XML.'
                    self.send_error(400, message=message)
                    return
            if nffg is None:
                self.send_error(400)
                return
            LOG.debug('Edit-config received: %s', nffg.xml())
            edit_config(nffg)
            self.write('config updated')
            return

        else:
            self.set_status(404)
            self.write_error(404)


def get_config():
    config = nffglib.Virtualizer.parse(file=CONFIG_FILE)
    config_xml = config.xml()
    LOG.debug('Sending config in response to get_config')
    return config_xml


def edit_config(requested_config):
    try:
        for node in requested_config.c_nodes.list_node:
            for requested_nf in node.c_NFInstances.list_node:
                """:type : nffglib.NodeGroup"""
                LOG.debug('nf requested: %s', requested_nf)
                # ToDo: instantiate requested_nf
    except:
        pass

    try:
        for node in requested_config.c_nodes.list_node:
            for requested_flowentry in node.g_flowtable.c_flowtable.list_flowentry:
                """:type : nffglib.FlowEntry"""
                LOG.debug('flow requested: %s', requested_flowentry)
                # ToDo: install requested_flowentry
    except:
        pass

    return


def start():
    LOG.debug('Start tornado server')
    app = Application([
        url(r"/(.*)", VirtualizationService)
    ])
    app.listen(8080)
    IOLoop.current().start()


if __name__ == '__main__':
    try:
        start()
    except KeyboardInterrupt:
        pass
