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
    -a <file>       The baseline test output (e.g. not batched case)
    -b <file>       The test output which needs to be compared to the baseline

    Outputs a sequence of percentages measuring how much test B improved 
    the performance throughtout the test.
"""

import getopt, sys

# Possible States
Init=0
StartAFound=1
Agood=2
StartBFound=3

def main(argv):
  try:
    opts, args = getopt.getopt(argv,"ha:b:",[])
  except getopt.GetoptError:
    print helpmsg
    sys.exit()

  filea = None
  fileb = None
  current_state = Init
  for opt, arg in opts:
    if opt == "-a":
      filea = arg
    elif opt == "-b":
      fileb = arg
    elif opt == "-h":
      print helpmsg
      sys.exit()

  with open(filea) as A:
    with open(fileb) as B:
        curr_seed = None
        perfA = None
        perfB = None
        lineB = None
        for lineA in A:
          try:
            if current_state == Init:
              if "Command" in lineA:
                current_state = StartAFound
                curr_seed = int(lineA.split(" ")[2])
            elif current_state == StartAFound:
              if "All-time peak" in lineA:
                current_state = Agood
                perfA = int(lineA.split(" ")[5].rstrip(","))
              elif "==========" in lineA:
                current_state = Init
                curr_seed = None
            elif current_state == Agood:
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
                if "All-time peak" in lineB:
                  perfB = int(lineB.split(" ")[5].rstrip(","))
                  print "%s\t%s\t%s"%(curr_seed, perfA,
                                        float(perfB - perfA)/perfA * 100.0)
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
