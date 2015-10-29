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
--stepsize=f     Sets the step size in the parameter space. Parameter intervals 
--maxstep=i      are [0.0, 3.0]. And the maximal number of how many of these 
                 steps can be taken at a time.
--seed=i         Random seed is needed for generating the probability. 
                 Determines the step sequence and step length sequence of the 
                 annealing. Default value is system time.
--test_seed=i    Needed to make the test requirement sequences deterministic.
--start_bw=f     Exactly two of the three parameters should be given as the 
--start_res=f    starting point for the annealing. The three parameters are
                 summed to 3.0. 
--start_temp=f   Sets the starting temerature.
--temp_step=f    Sets the decrementation of temperature during one step.
--maxidle=i      Defines how many iterations without moving to other parameter
                 points should cause the algorithm to exit.
--maxiters=i     The number of iterations to complete at most.
"""


log = logging.getLogger("SimulatedAnnealing")
log.setLevel(logging.DEBUG)
logging.basicConfig(format='%(levelname)s:%(name)s:%(message)s')

def evaluatePoint(bw, res, test_seed, error_file, queue=None,
                  shortest_paths=None):
  """
  If shortest_paths is None than, the calculated paths are sent back with the
  resulting point value as a tuple.
  NOTE: the same file can be written here simulaniously, but it is only used
  in case an exception is thrown and that is logged there.
  """
  lat = 3.0 - bw - res
  single_test = mp.Queue()
  shortest_paths_calced = None
  log.debug("Examination of point %s %s started..."%(bw,res))
  if shortest_paths is not None:
    mp.Process(target=st.StressTestCore, args=(test_seed, False, 0.0, False, 0, 
                                               False, bw, res, lat, error_file),
               kwargs={'queue':single_test, 
                       'shortest_paths_precalc':shortest_paths_calced, 
                       'filehandler':handler}).start()
    shortest_paths_sendback = False
    shortest_paths_calced = shortest_paths
  else:
    # don't give the Queue to it, we want it to calculate shortest path so
    # we could give it to the next two.
    shortest_paths_calced = st.StressTestCore(test_seed, False, 0.0, False, 0, 
                                              False, bw, res, lat, error_file, 
                                              queue=single_test, 
                                              filehandler=handler)
    shortest_paths_sendback = True

  multi_test = mp.Queue()
  mp.Process(target=st.StressTestCore, args=(test_seed, False, 0.3, True, 3, 
                                             False, bw, res, lat, error_file),
             kwargs={'queue':multi_test, 
                     'shortest_paths_precalc':shortest_paths, 
                     'filehandler':handler}).start()
  shared_test = mp.Queue()
  mp.Process(target=st.StressTestCore, args=(test_seed, False, 0.2, False, 0,
                                             False, bw, res, lat, error_file),
             kwargs={'queue':shared_test, 
                     'shortest_paths_precalc':shortest_paths_calced, 
                     'filehandler':handler}).start()
  
  # wait all three test sequences to finish
  result_vector = (single_test.get(), 
                   multi_test.get(),
                   shared_test.get())
  for result, test in zip(result_vector, ("single", "multi", "shared")):
    if issubclass(result.__class__, (Exception, Warning)):
      log.warn("An exception was thrown by the \"%s\" StressTest: %s"%
               (test, result.msg if hasattr(result, 'msg') else result))
      if queue is not None:
        queue.put(((bw, res), 0.0))
      if shortest_paths_sendback:
        return 0.0, shortest_paths_calced
      else:
        return 0.0
  # the length of the result vector is the value
  value = math.sqrt(reduce(lambda a, b: a+b*b, result_vector, 0))
  log.debug("Examination of point %s %s finished, scores are: %s"%
            (bw,res,result_vector))
  if queue is not None:
    queue.put(((bw, res), value))
  if shortest_paths_sendback:
    return value, shortest_paths_calced
  else:
    return value

def checkEvalCache(cache, point, delta=0.05):
  for p in cache:
    if math.fabs(p[0] - point[0]) < delta and math.fabs(p[1] - point[1]) < delta:
      return p, cache[p]
  return None, None

def rotateVector(v, deg):
  x = v[0]
  y = v[1]
  rad = deg/180.0 * math.pi
  return x*math.cos(rad) - y*math.sin(rad), x*math.sin(rad) + y*math.cos(rad)

if __name__ == '__main__':
  try: 
    opts, args = getopt.getopt(sys.argv[1:],"ho:", ["neighbor_cnt=", "stepsize=", 
                                                    "maxstep=", "test_seed=",
                                                    "seed=", "start_res=", 
                                                    "start_bw=", "start_temp=",
                                                    "temp_step=", "maxidle=",
                                                    "maxiters="])
    baseoutfile = "simulannealing"
    stepsize = 0.05
    maxstep = 6
    bw = None
    res = None
    maxiters = 30
    neighbor_cnt = 4
    seed = math.floor(time.time())
    test_seed = 0
    start_temp = 100
    temp_step = 5
    maxidle = 10
    for opt, arg in opts:
      if opt == "-h":
        print helpmsg
        sys.exit()
      elif opt == "-o":
        baseoutfile = arg
      elif opt == "--seed":
        seed = int(arg)
      elif opt == "--test_seed":
        test_seed = int(arg)
      elif opt == "--stepsize":
        stepsize = float(arg)
      elif opt == "--maxstep":
        maxstep = float(arg)
      elif opt == "--start_bw":
        bw = float(arg)
      elif opt == "--start_res":
        res = float(arg)
      elif opt == "--neighbor_cnt":
        neighbor_cnt = int(arg)
      elif opt == "--start_temp":
        start_temp = float(arg)
      elif opt == "--temp_step":
        temp_step = float(arg)
      elif opt == "--maxidle":
        maxidle = int(arg)
      elif opt == "--maxiters":
        maxiters = int(arg)
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
  handler = logging.FileHandler(baseoutfile, 'w',)
  log.addHandler(handler)
  point_eval_cache = {}
  idlehistory = []
  for i in range(0,maxidle):
    idlehistory.append(False)
  # evaluate the starting point and receive the shortest path for speeding up
  currvalue, shortest_paths = evaluatePoint(current[0], current[1], test_seed, 
                                            baseoutfile)
  if shortest_paths is None:
    raise Exception("The evaluation of starting point and thus shortest path "
                    "calculation is failed!")
  else:
      point_eval_cache[current] = currvalue
  random.seed(seed)
  temperature = start_temp
  best = current
  bestvalue = currvalue
  x = random.random()
  y = random.random()
  length = math.sqrt(x*x + y*y)
  # this defines the tangent of the net in the parameter space where we will
  # continue searching. The annealing can't escape from this net.
  netdirection = (x / length * stepsize, y / length * stepsize)
  while itercnt <= maxiters:
    try:
      step_number = random.randint(1, maxstep)
      v0 = (step_number*netdirection[0], step_number*netdirection[1])
      is_cached = []
      threads = []
      for i in range(0, neighbor_cnt):
        is_cached.append(False)
      # save the state of Random module before evaluating the points
      randomstate = random.getstate()
      # start every points evaluation in separate threads!
      results_q = mp.Queue(maxsize = neighbor_cnt)
      deg = 360 / float(neighbor_cnt)
      log.info("%i:Examining the %s-step neighbors of %s %s"%
               (itercnt,step_number,current[0],current[1]))
      for i in range(0, neighbor_cnt):
        v0_limited = list(v0)
        # preventing escaping from parameter space with boundaries.
        if current[0]+v0_limited[0] < 0 and math.fabs(v0_limited[0]) > 0.0001:
          v0_limited[1] = ((-1 * current[0]) / v0_limited[0]) * v0_limited[1]
          v0_limited[0] = -1 * current[0]
        if current[1]+v0_limited[1] < 0 and math.fabs(v0_limited[1]) > 0.0001:
          v0_limited[0] = ((-1 * current[1]) / v0_limited[1]) * v0_limited[0]
          v0_limited[1] = -1 * current[1]
        if current[0]+v0[0] + current[1]+v0[1] > 3 and \
           v0_limited[0] + v0_limited[1] > 0.0001 or \
           v0_limited[0] + v0_limited[1] < -0.0001:
          temp = list(v0_limited)
          v0_limited[0] = temp[0] * (3.0 - current[0] - current[1]) / \
                          (temp[0] + temp[1])
          v0_limited[1] = temp[1] * (3.0 - current[0] - current[1]) / \
                          (temp[0] + temp[1])
        point, pvalue = checkEvalCache(point_eval_cache, 
                                       (current[0]+v0_limited[0],
                                        current[1]+v0_limited[1]))
        if point == None and pvalue == None: 
          threads.append(
            mp.Process(target=evaluatePoint, args=(current[0]+v0_limited[0], 
                                                   current[1]+v0_limited[1], 
                                                   test_seed, baseoutfile), 
                       kwargs={'queue':results_q, 
                               'shortest_paths':shortest_paths}))
          threads[-1].start()
        else:
          log.debug("%i:Point %s %s was cached!"%(itercnt,point[0], point[1]))
          results_q.put((point, pvalue))
          is_cached[i] = True
        v0 = rotateVector(v0, deg)

      results_l = []
      # wait all evaluations to finish and decide where should we step forward
      for i in range(0, neighbor_cnt):
        result = results_q.get()
        log.debug("%i:Result received from neighbor number %s."%(itercnt,i))
        results_l.append(result)
        if not is_cached[i]:
          point_eval_cache[result[0]] = result[1]

      # restore random module state after points are evaluated.
      random.setstate(randomstate)

      # check whether the maximal move of the moveset is better than the current
      max_, maxvalue = max(results_l, key=lambda a: a[1])
      probability = math.e **(-(start_temp/6.0)/temperature)
      log.debug("%i:Max value of neighbors: %s "%(itercnt, maxvalue))
      log.debug("%i:Probability of accepting worse case: %s"%
                (itercnt, probability))
      if maxvalue >= currvalue:
        if math.fabs(maxvalue - currvalue) < 0.000001:
          idlehistory.append(True)
        else:
          idlehistory.append(False)
        current = max_
        currvalue = maxvalue
        log.info("%i:Accepted better point %s %s with value %s!"%
                 (itercnt,current[0],current[1],currvalue))
        if maxvalue >= bestvalue:
          best = max_
          bestvalue = maxvalue
          log.info("Overall best point %s %s found with value %s!"%
                   (best[0], best[1], bestvalue))
      elif random.random() < probability:
        # if not, we can still accept is with some probability
        current = max_
        currvalue = maxvalue
        log.debug("%i:Accepted worse point %s %s with value %s!"%
                  (itercnt, current[0], current[1], currvalue))
        idlehistory.append(False)
      else:
        log.debug("%i:Staying in place %s..."%(itercnt, current))
        idlehistory.append(True)

      # remove the oldest element
      idlehistory = idlehistory[1:]
      if reduce(lambda a,b: a and b, idlehistory):
        log.info("%i:The process stayed in place for %i consequent iterations"
                 "...Exiting..."%(itercnt, len(idlehistory)))
        break
      temperature = temperature-temp_step if temperature-temp_step > 0 else 0.0000001
      log.info("%i:Temperature is %s"%(itercnt, temperature))
      itercnt += 1
    except Exception:
      log.error(traceback.format_exc())
      # wait all the already started (in this iteration before the exception) 
      # threads to finish in order not to overload the matchine in case of some
      # consequent erronous iterations.
      for thread in threads:
        if thread.is_alive():
          thread.join()
      # The Queue for the result of the threads is reset in the beginning of 
      # next iteration.

      # needed to move the random module forward to possibly avoid the exception
      # in next iteration.
      random.random()
  log.info("Simulated Annealing finished!")
