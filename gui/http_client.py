try:
  import httplib as httpclient
  import urlparse as url
except:
  import http.client as httpclient
  import urllib.parse as url


class GetClient():
  def __init__ (self, httpAddress=None):
    self.__address = httpAddress
    # temporary nffg storage
    self.__nffg = None

  def getNFFG (self, address=None):
    if not address == None:
      self.__address = address
    try:
      if not "http://" in self.__address[:7] \
         and not "https://" in self.__address:
        self.__address = 'http://' + self.__address
      scheme, netloc, path, params, query, fragment = url.urlparse(
        self.__address)
      if netloc == '' or netloc is None:
        # assume localhost
        netloc = 'localhost'
      print "scheme: %s net location: %s path: %s" % (scheme, netloc, path)
      conn = httpclient.HTTPConnection(netloc, timeout=1)
      # TODO implement NFFG request according to ESCAPE API
      # for now only use a sample json file
      conn.request("POST", path)
      r1 = conn.getresponse()
      if r1.status != 200:
        raise ValueError("" % r1.reason)
      self.__nffg = r1.read()
    except:
      pass
    return self.__nffg
