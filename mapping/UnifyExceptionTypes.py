# Copyright (c) 2014 Balazs Nemeth
#
# This file is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This file is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with POX. If not, see <http://www.gnu.org/licenses/>.


from exceptions import Exception


class UnifyException(Exception):
  """
  Base class for all exceptions raised during the mapping process.
  """

  def __init__ (self, msg0):
    """Messages shall be constructed when raising the exception
    according to the actual circumstances."""
    self.msg = msg0


class InternalAlgorithmException(UnifyException):
  """
  Raised when the algorithm fails due to implementation error
  or conceptual error.
  """
  pass


class BadInputException(UnifyException):
  """
  Raised when the algorithm receives bad formatted, or unexpected input.
  Parameters shall be strings.
  """

  def __init__ (self, expected, given):
    self.msg = "The algorithm expected an input: %s, but the given input is: " \
               "%s" % (expected, given)


class MappingException(UnifyException):
  """
  Raised when a mapping could not be found for the request given from the
  upper layer. Not enough resources, no path found.

  :param peak_vnf_cnt: the peak number of VNFs mapped at the same time
  :type peak_vnf_cnt: int
  :param peak_sc_cnt: the number of subchain which couldn't be mapped last
  :type peak_sc_cnt: int
  :return: a MappingException object
  :rtype: :any:`MappingException`
  """

  def __init__(self, msg, backtrack_possible, 
               peak_vnf_cnt=None, peak_sc_cnt=None):
    super(MappingException, self).__init__(msg + " Backtrack available: %s"
                                           %backtrack_possible)
    self.backtrack_possible = backtrack_possible
    self.peak_mapped_vnf_count = peak_vnf_cnt
    self.peak_sc_cnt = peak_sc_cnt
