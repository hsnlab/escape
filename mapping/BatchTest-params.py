import subprocess, getopt, sys, threading, os
import numpy as np

helpmsg="""
Script to give start and give parameters to BatchTests.

   --stress_type=<<agressive|normal|decent|    The name of the available 
                   sc8decent|small>>           StressTest-*.py script to be used.
   --seed_start=i          The starting seed for the test sequences
   --seed_end=i            The end seed for the test sequences
   -t                      If set, time is measured for each StressTest.
   --batch_length=f        The number of SG-s / time to wait to batch together.
   --bt_limit=i            Backtracking depth limit of mapping.
   --bt_br_factor=i        Branching factor of bactracking of mapping.
   --poisson               Make the StressTest run in poisson (not all of them 
                           supports it)

   --batch_length_end=f
   --batch_step=f

   --bt_limit_end=i

   --dump_nffgs=i         Dump every 'i'th NFFG of a test sequence.

   --topo_name=<<>>
   --single_test          Sets 'map_only_first_batch' to the StressTest-*.py
   --milp                 Use Mixed Integer Linear Programming instead of the
                          heuristic algorithm.
   --threads=i            Sets the maximal parallel thread count during testing.
"""

semaphore = None
sem_bt_batch = {}

class Test(threading.Thread):
    
    def __init__(self, command, outputfile, i, bt, batch):
        threading.Thread.__init__(self)
        self.command = command
        self.outputfile = outputfile
        self.i = i
        self.semkey = (bt,batch)

    def run(self):
        semaphore.acquire()
        sem_bt_batch[self.semkey].acquire()

        with open(self.outputfile, "a") as f:
            f.write("\nCommand seed: %s\n"%self.i)
        print "Executing: ", self.command

        os.system(self.command)

        with open(self.outputfile, "a") as f:
            f.write("\n============================================\n")

        sem_bt_batch[self.semkey].release()
        semaphore.release()


def main(argv):
    try:
        opts, args = getopt.getopt(argv,"ht",["stress_type=", "seed_start=", 
                                              "seed_end=", "batch_length=", 
                                              "bt_limit=", "bt_br_factor=",
                                              "poisson", "batch_length_end=",
                                              "batch_step=", "bt_limit_end=",
                                              "dump_nffgs=", "topo_name=", 
                                              "single_test", "milp", "threads="])
    except getopt.GetoptError as goe:
        print helpmsg
        raise
    stress_type = None
    seed_start = 0
    seed_end = 10
    time = False
    poisson = False
    batch_length = 1.0
    bt_limit = 6
    bt_br_factor = 3
    dump_nffgs = False
    dump_cnt = 1
    topo_name = "gwin"
    single_test = False
    milp = False
    max_thread_cnt = 4
    for opt, arg in opts:
        if opt == "-h":
            print helpmsg
            sys.exit()
        elif opt == "-t":
            time = True
        elif opt == "--stress_type":
            stress_type = arg
        elif opt == "--seed_start":
            seed_start = int(arg)
        elif opt == "--seed_end":
            seed_end = int(arg)
        elif opt == "--batch_length":
            batch_length = float(arg)
        elif opt == "--bt_limit":
            bt_limit = int(arg)
        elif opt == "--bt_br_factor":
            bt_br_factor = int(arg)
        elif opt == "--poisson":
            poisson = True
        elif opt == "--dump_nffgs":
            dump_nffgs = True
            dump_cnt = int(arg)
        elif opt == "--topo_name":
            topo_name = arg
        elif opt == "--single_test":
            single_test = True
        elif opt == "--milp":
            milp = True
        elif opt == "--threads":
            max_thread_cnt = int(arg)

    batch_length_end = batch_length + 0.0000001
    batch_step = 1
    bt_limit_end = bt_limit + 1
    for opt, arg in opts:
        if opt == "--batch_step":
            batch_step = float(arg)
        elif opt == "--batch_length_end":
            batch_length_end = float(arg)
        elif opt == "--bt_limit_end":
            bt_limit_end = int(arg) + 1

    # batch_length_end += batch_step

    if stress_type is None:
        print "StressTest type must be given!"
        print helpmsg
        sys.exit()

    global semaphore
    semaphore = threading.Semaphore(max_thread_cnt)
    
    # ensures no files are written parallely by two or more processes
    for bt in xrange(bt_limit, bt_limit_end):
        for batch in np.arange(batch_length, batch_length_end, batch_step):
            sem_bt_batch[(bt,batch)] = threading.Semaphore(1)

    for i in xrange(seed_start,seed_end):
        for bt in xrange(bt_limit, bt_limit_end):
            for batch in np.arange(batch_length, batch_length_end, batch_step):

                outputfile = "batch_tests/gw-"+("poi-" if poisson else "")+\
                             "%s-%sbatched-seed%s-%s-bt%s-%s.out"\
                             %(stress_type, batch, seed_start, seed_end, bt, 
                               bt_br_factor)
                commtime = "/usr/bin/time -o "+outputfile+" -a -f \"%U user,\t%S sys,\t%E real\" "
                commbatch = "python StressTest-%s.py --bw_factor=0.5 --lat_factor=2.0 --res_factor=0.5 --shareable_sg_count=4 --topo_name=%s %s --batch_length=%s --bt_limit=%s --bt_br_factor=%s --request_seed="%\
                            (stress_type, topo_name, ("--dump_nffgs="+str(dump_cnt)+",nffgs-seed"+str(i)+"-"+outputfile.rstrip(".out") if dump_nffgs else ""), batch, bt, bt_br_factor)

                if time:
                    commbatch = commtime + commbatch

                command = commbatch + str(i) + (" --milp " if milp else "") + \
                          (" --map_only_first_batch " if single_test else "") + \
                          (" --poisson 2>> " if poisson else " 2>> ") + outputfile

                Test(command, outputfile, i, bt, batch).start()


if __name__ == '__main__':
    main(sys.argv[1:])
    
