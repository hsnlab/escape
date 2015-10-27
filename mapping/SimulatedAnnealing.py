#!/usr/bin/env python
# Copyright (c) 2015 Balazs Nemeth
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
Parameterizable simulated annealing procedure on the parameter space of 
res_factor, lat_factor, bw_factor. To find the best parameter setting of 
the algorithm on the given topology. Algorithm settings are evaluated based
on the different kind of stress tests.
"""

import sys, getopt, traceback, threading, time, math, random, logging
import StressTest as st
import multiprocessing as mp

helpmsg = """SimulatedAnnealing.py usage:
-h               Print this help message.
-o               Output file for logging visualizable parameters of the 
                 procedure.
--neighbor_cnt=i Sets the number of neighboring parameter space points to examine
                 All of them are evaluated in separate threads. 
                 Default value is 4.
--minstep=f      Sets the step size in the parameter space. Parameter intervals 
--maxstep=f      are [0.0, 3.0].
--seed=i         Random seed is needed for generating the probability. (Adviced 
                 to use only for debugging to generate deterministic step 
                 sequence.)
--test_seed=i    Needed to make the test requirement sequences deterministic.
--start_bw=f     Exactly two of the three parameters should be given as the 
--start_res=f    starting point for the annealing. The three parameters are
                 summed to 3.0. 
"""


log = logging.getLogger("SimulatedAnnealing")
log.setLevel(logging.DEBUG)
logging.basicConfig(format='%(levelname)s:%(name)s:%(message)s')
handler = logging.FileHandler('simulated_annealing.log', 'w',)
log.addHandler(handler)

def evaluatePoint(bw, res, test_seed, error_file, queue=None,
                  shortest_paths=None):
  """
  If shortest_paths is None than, the calculated paths are sent back with the
  resulting point value as a tuple.
  NOTE: the same file can be written here simulaniously, but it is only used
  in case an exception is thrown and that is logged there.
  """
  lat = 3.0 - bw - res
  multi_test = mp.Queue()
  shortest_paths_calced = None
  log.debug("Examination of point %s,%s started..."%(bw,res))
  if shortest_paths is not None:
    mp.Process(target=st.StressTestCore, args=(test_seed, False, 0.3, True, 3, 
                                               True, bw, res, lat, error_file),
               kwargs={'queue':multi_test, 
                       'shortest_paths_precalc':shortest_paths, 
                       'filehandler':handler}).start()
    shortest_paths_sendback = False
    shortest_paths_calced = shortest_paths
  else:
    # don't give the Queue to it, we want it to calculate shortest path so
    # we could give it to the next two.
    shortest_paths_calced = st.StressTestCore(test_seed, False, 0.3, True, 3, 
                                              True, bw, res, lat, error_file, 
                                              queue=multi_test, 
                                              filehandler=handler)
    shortest_paths_sendback = True

  single_test = mp.Queue()
  mp.Process(target=st.StressTestCore, args=(test_seed, False, 0.0, False, 0, 
                                             True, bw, res, lat, error_file), 
             kwargs={'queue':single_test, 
                     'shortest_paths_precalc':shortest_paths_calced, 
                     'filehandler':handler}).start()
  shared_test = mp.Queue()
  mp.Process(target=st.StressTestCore, args=(test_seed, False, 0.2, False, 0,
                                             True, bw, res, lat, error_file),
             kwargs={'queue':shared_test, 
                     'shortest_paths_precalc':shortest_paths_calced, 
                     'filehandler':handler}).start()
  
  # wait all three test sequences to finish
  result_vector = (multi_test.get(), single_test.get(), shared_test.get())
  for res, test in zip(result_vector, ("multi", "single", "shared")):
    if issubclass(res.__class__, (Exception, Warning)):
      log.warn("An exception was thrown by the \"%s\" StressTest: %s"%(test, 
                                                                       res))
      if shortest_paths_sendback:
        return 0.0, None
      else:
        return 0.0
  # the length of the result vector is the value
  value = math.sqrt(reduce(lambda a, b: a+b*b, result_vector, 0))
  log.debug("Examination of point %s,%s finished, scores are: %s"%
            (bw,res,result_vector))
  if queue is not None:
    queue.put(((bw, res), value))
  if shortest_paths_sendback:
    return value, shortest_paths_calced
  else:
    return value

def rotateVector(v, deg):
  x = v[0]
  y = v[1]
  rad = deg/180.0 * math.pi
  return x*math.cos(rad) - y*math.sin(rad), x*math.sin(rad) + y*math.cos(rad)

if __name__ == '__main__':
  try: 
    opts, args = getopt.getopt(sys.argv[1:],"ho:", ["neighbor_cnt=", "minstep=", 
                                                    "maxstep=", "test_seed=",
                                                    "seed=", "start_res=", 
                                                    "start_bw="])
    baseoutfile = "simulannealing"
    minstep = 0.05
    maxstep = 0.3
    bw = None
    res = None
    maxiters = 200
    neighbor_cnt = 4
    seed = math.floor(time.time())
    test_seed = 0
    for opt, arg in opts:
      if opt == "-h":
        print helpmsg
        sys.exit()
      elif opt == "-o":
        baseoutfile = arg
      elif opt == "--threads":
        threads = int(arg)
      elif opt == "--seed":
        seed = int(arg)
      elif opt == "--test_seed":
        test_seed = int(arg)
      elif opt == "--minstep":
        minstep = float(arg)
      elif opt == "--maxstep":
        maxstep = float(arg)
      elif opt == "--start_bw":
        bw = float(arg)
      elif opt == "--start_res":
        res = float(arg)
      elif opt == "--neighbor_cnt":
        neighbor_cnt = int(arg)
    if bw is None or res is None:
      raise Exception("Starting parameters must be given!")
    elif bw + res > 3.0:
      raise Exception("The sum of params shouldn't get above 3.0!")
  except Exception as e:
    print traceback.format_exc()
    print helpmsg
    sys.exit()


  itercnt = 0
  current = (bw, res)
  # evaluate the starting point and receive the shortest path for speeding up
  currvalue, shortest_paths = evaluatePoint(current[0], current[1], test_seed, 
                                            baseoutfile)
  random.seed(seed)
  temperature = 100
  while itercnt <= maxiters:
    step = random.random() * (maxstep - minstep) + minstep
    x = random.random()
    y = random.random()
    length = math.sqrt(x*x + y*y)
    v0 = (x / length * step, y / length * step)
    # save the state of Random module before evaluating the points
    randomstate = random.getstate()
    # start every points evaluation in separate threads!
    results_q = mp.Queue(maxsize = neighbor_cnt)
    deg = 360 / float(neighbor_cnt)
    log.info("Examining the neighbors of %s,%s"%(current[0],current[1]))
    for i in range(0, neighbor_cnt):
      mp.Process(target=evaluatePoint, args=(current[0]+v0[0], current[1]+v0[1], 
                                             test_seed, baseoutfile), 
                 kwargs={'queue':results_q, 'shortest_paths':shortest_paths})\
        .start()
      v0 = rotateVector(v0, deg)
      
    results_l = []
    # wait all evaluations to finish and decide where should we step forward
    for i in range(0, neighbor_cnt):
      result = results_q.get()
      log.debug("Result received from neighbor number %s."%i)
      results_l.append(result)

    # restore random module state after points are evaluated.
    random.setstate(randomstate)
    
    # check whether the maximal move of the moveset is better than the current
    max_, maxvalue = max(results_l, key=lambda a: a[1])
    probability = math.e **(-(currvalue-maxvalue)/temperature)
    log.debug("Max value of neighbors: %s "%maxvalue)
    log.debug("Probability of accepting worse case: %s"%probability)
    if maxvalue >= currvalue:
      current = max_
      currvalue = maxvalue
      log.info("Accepted better point with value %s!"%currvalue)
    elif random.random() < probability:
      # if not, we can still accept is with some probability
      current = max_
      currvalue = maxvalue
      log.debug("Accepted worse point with value %s!"%currvalue)
    else:
      log.debug("Staying in place...")
      
    temperature = temperature-1 if temperature-1 > 0 else 0.0000001
    
    itercnt += 1
