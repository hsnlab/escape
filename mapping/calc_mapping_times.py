"""
Calculates how much time (averaged on the seeds) does it take for all the 
batchings (increasing in size) to map by either MILP or Alg1. Considers only the
successful mappings.
"""

map_times = {}
cnts = {}
mins = {}
maxs = {}
for b in xrange(4, 300, 4):
  map_times[b] = 0.0
  cnts[b] = 0
  mins[b] = float('inf')
  maxs[b] = 0
for b in xrange(4, 300, 4):
  base = "batch_tests/gw-small-%s.0batched-seed0-100-bt6-3.out"%b
  with open(base, "r") as f:
    for line in f:
      line = line.split(" ")
      if line[0] == "Command":
        try:
          if next(f).rstrip('\n') == "WARNING:StressTest:Mapping only the first"\
             " batch finished successfully!":
            real_time = next(f).rstrip('\n').split('\t')[2].split(' ')
            if real_time[1] == "real":
              time = 60.0*float(real_time[0].split(':')[0]) + \
                     float(real_time[0].split(':')[1])
              map_times[b] += time
              cnts[b] += 1
              if maxs[b] < time:
                maxs[b] = time
              if mins[b] > time:
                mins[b] = time
        except StopIteration:
          pass

print "sc_count, avg_running_time, min_running_time, max_running_time, sample_size"
for b in xrange(4, 300, 4):
  print "%s, %s, %s, %s, %s"%(b, map_times[b]/cnts[b] if cnts[b]>0 else "N/A", 
                              mins[b], maxs[b], cnts[b])
