"""
Calculates how many requests can be mapped at most according to the MILP
 mapping solution for each seed.
Calculates the average number of requests that can be embedded onto the same
shared network.
"""

top_success = {}
for s in xrange(0,100):
  top_success[s] = 0
for b in xrange(4, 300, 4):
  base = "milp-tests/lab30/gw-small-%s.0batched-seed0-100-bt6-3.out"%b
  with open(base, "r") as f:
    for line in f:
      line = line.split(" ")
      if line[0] == "Command":
        seed = int(line[2])
        if next(f).rstrip('\n') == "WARNING:StressTest:Mapping only the first"\
           " batch finished successfully!" and b > top_success[seed]:
          top_success[seed] = b

for s, b in top_success.iteritems():
  print s, ", ", b
