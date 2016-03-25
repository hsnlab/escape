# Copyright (c) 2016 Balazs Nemeth
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

"""
Script to analyze the difference between two BatchTest-*.py output files.
"""

helpmsg="""
Usage:
    -a <file>       The baseline test output (e.g. not batched case)
    -b <file>       The test output which needs to be compared to the baseline

    --nfs           If set, the performacen will be measured based on the peak 
                    mapped NF count of both test outputs. Otherwise only the 
                    test level is considered.
    --permissive    If set, all-time total VNF is also taken into account, and 
                    if it is larger than the peak mapped VNF count, the 
                    performance is considered the same. Only works if --nfs is 
                    also set.

    Outputs a sequence of percentages measuring how much test B improved 
    the performance throughtout the test.
"""

import getopt, sys

# Possible States
Init=0
StartAFound=1
Agood=2
StartBFound=3
Aprocessed = 4
Bprocessed = 5 

def main(argv):
  try:
    opts, args = getopt.getopt(argv,"ha:b:",["nfs", "permissive"])
  except getopt.GetoptError as goe:
    print helpmsg
    raise

  filea = None
  fileb = None
  current_state = Init
  nfs = False
  permissive = False
  for opt, arg in opts:
    if opt == "-a":
      filea = arg
    elif opt == "-b":
      fileb = arg
    elif opt == "--nfs":
      nfs = True
    elif opt == "--permissive":
      permissive = True
    elif opt == "-h":
      print helpmsg
      sys.exit()

  with open(filea) as A:
    with open(fileb) as B:
        curr_seed = None
        perfA = None
        perfB = None
        lineB = None
        timeA = None
        timeB = None
        vnfcountA = None
        if nfs:
          print "Seed\tNFcnt\tImprove[%]\tTimeA[s]\tTimeB[s]"
        else:
          print "Seed\tTestlvl\tImprove[%]\tTimeA[s]\tTimeB[s]"
        for lineA in A:
          try:
            if current_state == Init:
              if "Command" in lineA:
                current_state = StartAFound
                curr_seed = int(lineA.split(" ")[2])
            elif current_state == StartAFound:
              if not nfs and "Peak mapped VNF" in lineA:
                current_state = Agood
                perfA = int(lineA.split(" ")[12])
              elif nfs and "All-time peak" in lineA:
                current_state = Agood
                perfA = int(lineA.split(" ")[5].rstrip(","))
                if permissive:
                  vnfcountA = int(lineA.split(" ")[10].rstrip(","))
              elif "==========" in lineA:
                current_state = Init
                curr_seed = None
            elif current_state == Agood:
              if "real" in lineA and "sys" in lineA and "user" in lineA:
                num = map(int, lineA.split('\t')[2].split(' ')[0].split('.')[0].\
                          split(':'))
                timeA = 60*num[0] + num[1]
                current_state = Aprocessed
            elif current_state == Aprocessed:
              while True:
                lineB = next(B)
                if "Command" in lineB:
                  if curr_seed == int(lineB.split(" ")[2]):
                    current_state = StartBFound
                    break
                  elif curr_seed < int(lineB.split(" ")[2]):
                    current_state = Init
                    curr_seed = None
                    break
            elif current_state == StartBFound:
              while True:
                lineB = next(B)
                if not nfs and "Peak mapped VNF" in lineB:
                  perfB = int(lineB.split(" ")[12])
                  current_state = Bprocessed
                  break
                elif nfs and "All-time peak" in lineB:
                  perfB = int(lineB.split(" ")[5].rstrip(","))
                  if permissive and \
                     int(lineB.split(" ")[10].rstrip(",")) > vnfcountA and\
                     perfB < perfA:
                    perfB = perfA
                  current_state = Bprocessed
                  break
                elif "==========" in lineB:
                  current_state = Init
                  curr_seed = None
                  break
            elif current_state == Bprocessed:
              while True:
                lineB = next(B)
                if "real" in lineB and "sys" in lineB and "user" in lineB:
                  num = map(int, lineB.split('\t')[2].split(' ')[0].split('.')[0].\
                            split(':'))
                  timeB = 60*num[0] + num[1]
                  print "%s\t%s\t%0.6f\t%s\t%s"%(curr_seed, perfA, 
                        float(perfB - perfA)/perfA * 100.0,
                        timeA, timeB)
                  current_state = Init
                  curr_seed = None
                  break
                elif "==========" in lineB:
                  current_state = Init
                  curr_seed = None
                  break
          except StopIteration:
            break

if __name__ == '__main__':
  main(sys.argv[1:])
