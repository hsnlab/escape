import Tkinter as tk

from networkx_viewer import *


class CustomNodeToken(TkPassthroughNodeToken):
  def render (self, data, node_name):
    """
    Custom Node Token for NFFG
    """
    self.config(width=20, height=20)

    points = None
    self.marker = None
    marker_options = {}
    try:
      # Set color and other options
      marker_options = {data.get('pattern', 'fill'): data.get('color', 'red')}
      txt = data.get('name', None)
      typ = data.get('element type', '')
      if txt is None:
        txt = "%s_%s" % (typ, node_name)
      self.label = self.create_text(0, 0, text=txt)
      # Draw circle or square, depending on what the node said to do

      if 'SAP' == typ:
        marker_options['fill'] = 'green'
        self.marker = self.create_oval(0, 0, 20, 20, **marker_options)
      elif 'NF' == typ:
        marker_options['fill'] = 'blue'
        self.marker = self.create_rectangle(0, 0, 20, 20, **marker_options)
      elif 'INFRA' == typ:
        points = [0, 10, 10, 20, 20, 10, 10, 0]
        self.marker = self.create_polygon(points, **marker_options)
      else:
        self.marker = self.create_oval(0, 0, 20, 20, {'fill': 'black'})

      # Figure out how big we really need to be
      bbox = self.bbox(self.label)
      bbox = [abs(x) for x in bbox]
      br = (max((bbox[0] + bbox[2]), 20), max((bbox[1] + bbox[3]), 33))

      w = max(br[0], 20)
      h = max(br[1], 30)
      self.config(width=w, height=h)

      # Place label and marker
      mid = (int(br[0] / 2.0), h - 7)
      self.coords(self.label, mid)
      self.coords(self.marker, mid[0] - 10, 0, mid[0] + 10, 20)
      if points is not None:
        points = [0, 10, int(w / 2), 20, w, 10, int(w / 2), 0]
        self.coords(self.marker, tk._flatten(points))
    except:
      # could not get type, color and/or shape
      marker_options = {'fill': 'black',
                        'outline': 'black'}
      self.marker = self.create_rectangle(0, 0, 20, 20, {'fill': 'black'})

  def customize_menu (self, menu, item):
    """Ovewrite this method to customize the menu this token displays
    when it is right-clicked"""
    # TODO
    pass


class CustomEdgeToken(TkPassthroughEdgeToken):
  # increasing width of edge on bandwidth values
  __bw = [10, 100, 1000, 10000]

  def render (self):
    """Called whenever canvas is about to draw an edge.
    Must return dictionary of config options for create_line
    Available parameteres are listed in
    TkPassthroughEdgeToken._tk_line_options
    """
    cfg = {}
    w = 1
    try:
      # TODO handle different edge types
      cfg['fill'] = self.edge_data.get('color', 'red')
      linkB = self.edge_data.get('bandwidth', 10)
      for b in self.__bw:
        if linkB > b:
          w += 1
        else:
          break
    except:
      cfg['fill'] = 'red'
      w = 9
    t = self.edge_data.get('element type', None)
    if t is "SG":
      # handle SG nexthop
      cfg['fill'] = 'blue'
      # arrow must be none, first, both, last
      cfg['arrow'] = 'last'
      # arrowshape is a list with 3 numbers: length of tip and neck, length
      # of side of the arrow, width of arrow
      cfg['arrowshape'] = [40, 50, 8]
    elif t is "REQUIREMENT":
      # handle requirement link
      # arrow must be none, first, both, last
      cfg['arrow'] = 'last'
      # arrowshape is a list with 3 numbers: length of tip and neck, length
      # of side of the arrow, width of arrow
      cfg['arrowshape'] = [40, 50, 8]
      cfg['dash'] = 1
    elif t is "STATIC":
      # handle static edge links
      cfg['fill'] = 'black'
    elif t is "DYNAMIC":
      cfg['fill'] = 'black'
    else:
      cfg['arrow'] = 'last'
      cfg['arrowshape'] = [40, 50, 8]
    cfg['width'] = w
    return cfg

  def customize_menu (self, menu, item):
    """Ovewrite this method to customize the menu this token displays
    when it is right-clicked"""
    # TODO
    pass
