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
  """
  pass
