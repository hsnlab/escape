import sys, os, getopt, subprocess, copy
import numpy as np
from collections import OrderedDict
from pprint import pformat
import matplotlib.pyplot as plt
import matplotlib
import math


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
resource types. Prints them in ascending order of test levels in CSV format.
Removes the uncompressed NFFG after it is finished with its processing.
   -h                               Print this help message.
   -l <<NFFG.tgz location>>         Location of the *.nffg.tgz files.   
   --hist=<<aggregation size>>      If given, draws the histogram
                                    for the utilization of resource 
                                    components aggregating the values by the 
                                    given size.
   --add_hist_values                If set, non-zero values are written above the
                                    bars on the histogram.
   --hist_format=<<pdf|png|...>>    The format of the saved histograms. 
                                    PNG by default
   --starting_lvl=i                 Start the analyzation only after the given 
                                    test level.
   --one                            Exit after one NFFG processing
   --cdf_format=<<pdf|png|...>>     The format of the saved CDF, PNG by default.
   --cdf                            Produces images of Cumulative Distribution 
                                    Function in the format specified by
                                    --cdf_formatoption for each resource type.
   --print_avgs                     Print the average resource utilizations for 
                                    all processed NFFG-s in CSV format.
   --print_devs                     Print the deviations of resource utilizations
                                    for all processed NFFG-s in CSV format. 
                                    The --cdf option must be set too.
"""

def increment_util_counter(d, u, aggr_size):
  # coudl be binary search...
  prev_aggr = aggr_size
  for aggr in d:
    if aggr > u:
      d[prev_aggr] += 1
      return
    prev_aggr = aggr

def autolabel(rects, ax):
  # attach some text labels
  for rect in rects:
    height = rect.get_height()
    if height > 0.0:
      ax.text(rect.get_x() + rect.get_width()/2., 1.05*height,
              '%.2f' % height,
              ha='center', va='bottom')

def main(argv):
  try:
    opts, args = getopt.getopt(argv, "hl:", ["hist=", "add_hist_values", 
                                             "hist_format=", "starting_lvl=",
                                             "one", "cdf_format=", "cdf",
                                             "print_devs", "print_avgs"])
  except getopt.GetoptError as goe:
    print helpmsg
    raise
  loc_tgz = ""
  draw_hist = False
  reskeys = ['cpu', 'mem', 'storage', 'bandwidth']
  add_hist_values = False
  hist_format = "png"
  starting_lvl = 0
  process_only_one = False
  draw_cdf = False
  cdf_format = "png"
  print_avgs = False
  print_devs = False
  for opt, arg in opts:
    if opt == "-h":
      print helpmsg
      sys.exit()
    elif opt == "-l":
      loc_tgz = arg
    elif opt == "--hist":
      draw_hist = True
      hist_aggr_size = float(arg)
      hist = {}
      for res in reskeys + ['link_bw']:
        hist[res] = OrderedDict()
        for aggr in np.arange(hist_aggr_size, 1.0, hist_aggr_size):
          hist[res][float("%.4f"%aggr)] = 0
        hist[res][1.0] = 0
    elif opt == "--add_hist_values":
      add_hist_values = True
    elif opt == "--hist_format":
      hist_format = arg
    elif opt == "--starting_lvl":
      starting_lvl=int(arg)
    elif opt == "--one":
      process_only_one = True
    elif opt == "--cdf":
      draw_cdf = True
      cdf = {}
      for res in reskeys + ['link_bw']:
        cdf[res] = []
    elif opt == "--cdf_format":
      cdf_format = arg
    elif opt == "--print_devs":
      print_devs = True
    elif opt == "--print_avgs":
      print_avgs = True
      
  nffg_num_list = []
  bashCommand = "ls -x "+loc_tgz
  process = subprocess.Popen(bashCommand.split(), stdout=subprocess.PIPE)
  tgz_files =  process.communicate()[0]
  for filen in tgz_files.replace("\n", " ").split(" "):
    if 'test_lvl' in filen:
      nffg_num_list.append(int(filen.split('-')[1].split('.')[0]))
  nffg_num_list = sorted(filter(lambda x: x>=starting_lvl, nffg_num_list))
  
  if print_avgs:
    print "test_lvl, avg(link_bw), ",", ".join(["".join(["avg(",noderes,")"]) \
                                                for noderes in reskeys])
  if print_devs:
    print "test_lvl, ", ", ".join(["".join(["dev(",noderes,")"]) \
                                   for noderes in cdf])

  if draw_hist:
    empty_hist = copy.deepcopy(hist)
  if draw_cdf:
    empty_cdf = copy.deepcopy(cdf)
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
      if draw_hist:
        hist = copy.deepcopy(empty_hist)
      if draw_cdf:
        cdf = copy.deepcopy(empty_cdf)
      for noderes in reskeys:
        avgs[noderes] = 0.0
        cnts[noderes] = 0
        for i in nffg.infras:
          # only count nodes which had these resources initially
          if i.resources[noderes] > 1e-10:
            util = float(i.resources[noderes] - i.availres[noderes]) / \
                   i.resources[noderes]
            avgs[noderes] += util
            cnts[noderes] += 1
            if draw_hist:
              increment_util_counter(hist[noderes], util, hist_aggr_size)
            if draw_cdf:
              cdf[noderes].append(util)
        avgs[noderes] /= cnts[noderes]
      avg_linkutil = 0.0
      linkcnt = 0
      for l in nffg.links:
        if l.type == 'STATIC':
          link_util = float(l.bandwidth - l.availbandwidth) / l.bandwidth
          avg_linkutil += link_util
          linkcnt += 1
          if draw_hist:
            increment_util_counter(hist['link_bw'], link_util, hist_aggr_size)
          if draw_cdf:
            cdf['link_bw'].append(link_util)
      avg_linkutil /= linkcnt

      if print_avgs:
        to_print = [test_lvl, avg_linkutil]
        to_print.extend([avgs[res] for res in reskeys])
        print ",".join(map(str, to_print))
      
      if print_devs:
        avgs['link_bw'] = avg_linkutil
        devs = {}
        for res in cdf:
          devs[res] = math.sqrt(sum([(avgs[res]-u)**2 for u in cdf[res]]) / \
                                (len(cdf[res])-1))
        to_print = [test_lvl]
        to_print.extend([devs[res] for res in cdf])
        print ",".join(map(str, to_print))

    # delete the NFFG and its parent folders
    os.system("rm -rf nffgs-batch_tests/")

    if draw_hist:
      # normalize the histogram to [0,1], so the resource types could be plotted 
      # on the same bar chart
      for res in hist:
        sum_util_cnt = sum([hist[res][util_range] for util_range in hist[res]])
        for util_range in hist[res]:
          hist[res][util_range] = float(hist[res][util_range]) / sum_util_cnt
      # print "test_lvl", test_lvl, pformat(hist),"\n"

      # plot the histograms.
      fig, ax = plt.subplots()
      ax.set_ylim((0.00, 1.10))
      range_seq = np.array([float("%.4f"%(aggr/hist_aggr_size)) for aggr in \
                            np.arange(hist_aggr_size, 1.0, hist_aggr_size)])
      range_seq = np.append(range_seq, [1.0/hist_aggr_size])
      width = range_seq[-1] / (len(hist)+2) / len(range_seq)
      colors = iter(['r', 'g', 'b', 'c', 'y'])
      i = 0
      rects = []
      for res in hist:
        rect = ax.bar((range_seq - 1)* (len(hist)+2) * width + \
                      (i+4.5) * width,
                      [hist[res][util_range] for util_range in hist[res]], 
                      width, color = next(colors))
        rects.append((res, rect))
        i += 1
        if add_hist_values:
          autolabel(rect, ax)
      # ax.set_aspect(10)
      ax.set_ylabel("Ratio of network element counts to total count")
      ax.set_xlabel("Resource utilization intervals [%]")
      ax.set_xticks(range_seq * (len(hist)+2) * width)
      ax.set_xticklabels([str(int(100*util_range)) for util_range in hist['cpu']])
      ax.legend([r[0] for r in zip(*rects)[1]], zip(*rects)[0], ncol=5, 
                loc='upper left', fontsize=8, bbox_to_anchor=(0,1))
      plt.savefig('plots/hist-test_lvl-%s.%s'%(test_lvl, hist_format), 
                  bbox_inches='tight')
      plt.close(fig)
    
    if draw_cdf:
      # sort util values incrementing in each resource type
      for res in cdf:
        cdf[res] = sorted(cdf[res])
      fig, ax = plt.subplots()
      ax.set_xlim((-0.05, 1.05))
      ax.set_ylim((-0.05, 1.10))
      colors = iter(['r', 'g', 'b', 'c', 'y'])
      for res in cdf:
        last_point = (0, 0)
        vertical_step = 1.0/len(cdf[res])
        rescolor = next(colors)
        reslab = res
        for point in zip(cdf[res], 
                         np.append(np.arange(vertical_step, 1.0, vertical_step),
                                   [1.0])):
          plt.plot((last_point[0], point[0]), (last_point[1], point[1]), 
                   color=rescolor, lw=3, label=reslab)
          reslab = None
          last_point = point
        plt.plot((last_point[0], 1.0), (last_point[1], 1.0), 
                 color=rescolor, lw=3)
      ax.set_ylabel("Ratio of network element counts to total count")
      ax.set_xlabel("Resource utilization interval from 0 to x [%]")
      ax.set_xticks([float(i)/100 for i in xrange(0,101, 5)])
      ax.set_xticklabels([str(i) for i in xrange(0,101, 5)])
      ax.legend(bbox_to_anchor=(0,1), loc='upper left', ncol=5, fontsize=8)
      plt.savefig('plots/cdf-test_lvl-%s.%s'%(test_lvl, cdf_format), 
                  bbox_inches='tight')
      plt.close(fig)

    # maybe finish after one iteration
    if process_only_one:
      break

if __name__ == '__main__':
  main(sys.argv[1:])
