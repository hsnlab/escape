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
import os
import time
from collections import namedtuple

from escape.util.config import PROJECT_ROOT
from escape.util.misc import Singleton
from pox.core import core

log = core.getLogger("STAT")

_StatEntry = namedtuple("StatEntry",
                        ('id', 'type', 'info', 'cmd', 'timestamp'))
"""Timestamp class for memory efficient storing."""


class StatTimestamp(_StatEntry):
  """
  Container class for storing information of a specific timestamp.
  """

  def dump (self):
    """
    :return: Return the timestamp info in a merged string.
    :rtype: str
    """
    return ",".join((str(self.id),
                     OrchestrationStatCollector.get_type_name(self.type),
                     str(self.info),
                     str(self.cmd),
                     "%f" % self.timestamp))


class OrchestrationStatCollector(object):
  """
  Manager class to collect and persist timestamp values of an orchestration
  process.
  """
  __metaclass__ = Singleton

  PREFIX = 'TYPE_'
  TYPE_OVERALL = 0
  TYPE_SCHEDULED = 1
  TYPE_SERVICE = 2
  TYPE_SERVICE_MAPPING = 21
  TYPE_ORCHESTRATION = 3
  TYPE_ORCHESTRATION_MAPPING = 31
  TYPE_DEPLOY = 4
  TYPE_DEPLOY_DOMAIN = 41
  TYPE_DEPLOY_REQUEST = 42
  TYPE_PROCESSING = 5
  TYPE_CONVERSION = 6
  CMD_START = "START"
  CMD_STOP = "END"

  def __init__ (self, stat_folder):
    """
    Init.

    :param stat_folder: location of the stat file
    :type stat_folder: str
    :return: None
    """
    self.stat_folder = stat_folder
    log.debug("Setup stat collector with folder: %s" % stat_folder)
    self.__cntr = 0
    self.__measured_values = []
    self.__request_id = None
    if not os.path.exists(self.stat_folder):
      os.mkdir(self.stat_folder)
    self.clear_stats()

  def set_request_id (self, request_id):
    """
    Set the request Id of the service request under orchestration.

    :param request_id: service request id
    :type request_id: str or int
    :return: None
    """
    self.__request_id = request_id

  @classmethod
  def get_type_name (cls, number):
    """
    Return the type name related to the given type number.

    :param number: type number
    :type number: int
    :return: type name
    :rtype: str
    """
    for t in cls.__dict__.keys():
      if t.startswith(cls.PREFIX) and getattr(cls, t) == number:
        return t[len(cls.PREFIX):]

  def __increase_cntr (self):
    """
    Increase unique counter.

    :return: increased counter
    :rtype: int
    """
    self.__cntr += 1
    return self.__cntr

  def clear_stats (self):
    """
    Remove unnecessary stat files.

    :return: None
    """
    log.debug("Remove stats files...")
    for f in os.listdir(os.path.join(PROJECT_ROOT, self.stat_folder)):
      if f != ".placeholder":
        os.remove(os.path.join(PROJECT_ROOT, self.stat_folder, f))

  def init_request_measurement (self, request_id):
    """
    Initialize measurement of a service request orchestration.

    :param request_id: service request id
    :type request_id: str or int
    :return: None
    """
    if self.__request_id != request_id:
      self.reset()
    self.__request_id = request_id
    self.add_measurement_start_entry(type=self.TYPE_OVERALL,
                                     info=self.__request_id)

  def finish_request_measurement (self):
    """
    Stop measurement of the actual service request orchestration and dump
    result into file.

    :return: None
    """
    self.add_measurement_end_entry(type=self.TYPE_OVERALL,
                                   info=self.__request_id)
    self.dump_to_file()

  def reset (self):
    """
    Clear measurement values.

    :return: None
    """
    self.__request_id = None
    del self.__measured_values[:]

  def add_measurement_start_entry (self, type, info=None):
    """
    Add a starting timestamp with the given parameters to the statistic.

    :param type: timestamp type
    :type type: str
    :param info: additional info
    :type info: str
    :return: None
    """
    se = StatTimestamp(id=self.__increase_cntr(),
                       type=type,
                       info=info,
                       cmd=self.CMD_START,
                       timestamp=time.time())
    log.debug("Measurement timestamp: %s" % str(se))
    self.__measured_values.append(se)

  def add_measurement_end_entry (self, type, info=None):
    """
    Add a ending timestamp with the given parameters to the statistic.

    :param type: timestamp type
    :type type: str
    :param info: additional info
    :type info: str
    :return: None
    """
    se = StatTimestamp(id=self.__increase_cntr(),
                       type=type,
                       info=info,
                       cmd=self.CMD_STOP,
                       timestamp=time.time())
    log.debug("Measurement timestamp: %s" % str(se))
    self.__measured_values.append(se)

  def raw_stat (self):
    """
    :return: Return the list of raw measured values
    :rtype: list
    """
    return self.__measured_values

  def _get_measured_types (self):
    """
    :return: Return the types of the stored timestamps.
    :rtype: set
    """
    return {mv.type for mv in self.__measured_values}

  def calculate_stat_values (self):
    """
    Process the raw timestamps and conclude derived measurements.

    :return: derived measurements
    :rtype: str
    """
    processed = []
    for _type in self._get_measured_types():
      if _type != self.TYPE_DEPLOY_DOMAIN:
        values = [e.timestamp for e in self.__measured_values if
                  e.type == _type]
        processed.append("%s: %s" % (self.get_type_name(_type),
                                     max(values) - min(values)))
      else:
        for dd in self.__measured_values:
          if dd.type == self.TYPE_DEPLOY_DOMAIN and dd.cmd == self.CMD_START:
            for e in self.__measured_values[dd.id:]:
              if e.info.startswith(dd.info):
                processed.append("- %s: %s" % (dd.info,
                                               e.timestamp - dd.timestamp))
    return processed

  def dump_to_file (self, file_name=None, raw=True, calculated=False):
    """
    Dump the measured timestamps into a file.

    :param file_name: use explicit file name
    :type file_name: str
    :param raw: dump raw measurements
    :type raw: bool
    :param calculated: dump derived measurements
    :type calculated: bool
    :return: None
    """
    if not file_name:
      file_name = "%s/%s.stat" % (self.stat_folder, self.__request_id)
    if os.path.exists(file_name):
      log.warning("Stat file for request already exists: %s! Overwriting..."
                  % file_name)
    with open(file_name, "w") as f:
      if raw:
        for line in self.raw_stat():
          f.write(line.dump() + '\n')
      f.write('=' * 80 + '\n')
      if calculated:
        for line in self.calculate_stat_values():
          f.write(line + '\n')
    log.info("Stat for service request is dumped into: %s" % file_name)


stats = OrchestrationStatCollector(PROJECT_ROOT + "/log/stats")
