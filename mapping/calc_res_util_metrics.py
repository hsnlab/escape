import sys, os
import subprocess

try:
  from escape.nffg_lib.nffg import NFFG
except ImportError:
  import sys, os
  sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__),
                                  "../pox/ext/escape/nffg_lib/")))
  from nffg import NFFG

helpmsg="""
Decompresses the NFFG-s given in command line, sorts them base on test level,
and calculates the average and deviation of link/node resources for all 
resource types. Prints them in ascending order of test levels.
Removes the uncompressed NFFG after it is finished with its processing.
"""

def main(argv):
  nffg_num_list = []
  loc_tgz = argv[0]
  bashCommand = "ls -x "+loc_tgz
  process = subprocess.Popen(bashCommand.split(), stdout=subprocess.PIPE)
  tgz_files =  process.communicate()[0]
  for filen in tgz_files.replace("\n", " ").split(" "):
    if 'test_lvl' in filen:
      nffg_num_list.append(int(filen.split('-')[1].split('.')[0]))
  nffg_num_list = sorted(nffg_num_list)
  
  reskeys = {'cpu', 'mem', 'storage', 'bandwidth'}

  print "test_lvl, avg(link_bw), ",", ".join([noderes for noderes in reskeys])

  for test_lvl in nffg_num_list:
    filename = "test_lvl-%s.nffg.tgz"%test_lvl
    os.system("".join(["tar -xf ",loc_tgz,"/",filename])) # decompress
    # after decompression nffg-s end up two folder deep.
    nffg_prefix = "nffgs-batch_tests/"+loc_tgz.split("/")[-1]+"/"
    with open("".join([nffg_prefix,"test_lvl-",str(test_lvl), ".nffg"]), 
              "r") as f:
      nffg = NFFG.parse(f.read())
      nffg.calculate_available_node_res()
      nffg.calculate_available_link_res([])
      # calculate avg. res utils by resource types.
      avgs = {}
      cnts = {}
      for noderes in reskeys:
        avgs[noderes] = 0.0
        cnts[noderes] = 0
        for i in nffg.infras:
          # only count nodes which had these resources initially
          if i.resources[noderes] > 1e-10:
            avgs[noderes] += float(i.availres[noderes]) / i.resources[noderes]
            cnts[noderes] += 1
        avgs[noderes] /= cnts[noderes]
      avg_linkutil = 0.0
      linkcnt = 0
      for l in nffg.links:
        if l.type == 'STATIC':
          avg_linkutil = float(l.availbandwidth) / l.bandwidth
          linkcnt += 1
      avg_linkutil /= linkcnt
      to_print = [test_lvl, avg_linkutil]
      to_print.extend([avgs[res] for res in reskeys])
      print ",".join(map(str, to_print))
    # delete the NFFG and its parent folders
    os.system("rm -rf nffgs-batch_tests/")

if __name__ == '__main__':
  main(sys.argv[1:])
