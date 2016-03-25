import subprocess, getopt, sys, threading
import numpy as np

helpmsg="""
Script to give start and give parameters to BatchTests.

   --stress_type=<<agressive|normal|decent|    The name of the available 
                   sc8decent>>                 StressTest-*.py script to be used.
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
"""

semaphore = threading.Semaphore(4)

class Test(threading.Thread):
    
    def __init__(self, command):
        threading.Thread.__init__(self)
        self.command = command

    def run(self):
        semaphore.acquire()
        os.system(self.command)
        semaphore.release()


def main(argv):
    try:
        opts, args = getopt.getopt(argv,"ht",["stress_type=", "seed_start=", 
                                              "seed_end=", "batch_length=", 
                                              "bt_limit=", "bt_br_factor=",
                                              "poisson", "batch_length_end=",
                                              "batch_step=", "bt_limit_end="])
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

    batch_length_end = batch_length + 0.0001
    batch_step = 1
    bt_limit_end = bt_limit + 1
    for opt, arg in opts:
        if opt == "--batch_step":
            batch_step = float(arg)
        elif opt == "--batch_length_end":
            batch_length_end = float(arg) + 1
        elif opt == "--bt_limit_end":
            bt_limit_end = int(arg) + 1

    if stress_type is None:
        print "StressTest type must be given!"
        print helpmsg
        sys.exit()
    
    for bt in xrange(bt_limit, bt_limit_end):
        for batch in np.arange(batch_length, batch_length_end, batch_step):

            outputfile = "batch_tests/"+("poi-" if poisson else "")+\
                         "%s-%sbatched-seed%s-%s-bt%s-%s.out"\
                         %(stress_type, batch, seed_start, seed_end, bt, 
                           bt_br_factor)
            commtime = "/usr/bin/time -o "+outputfile+" -a -f \"%U user,\t%S sys,\t%E real\" "
            commbatch = "python StressTest-%s.py --bw_factor=0.5 --lat_factor=2.0 --res_factor=0.5 --shareable_sg_count=4 --batch_length=%s --bt_limit=%s --bt_br_factor=%s --request_seed="%(stress_type, batch, bt, bt_br_factor)

            if time:
                commbatch = commtime + commbatch

            for i in xrange(seed_start,seed_end):
                command = commbatch + str(i) + (" --poisson 2>> " if poisson else " 2>> ") \
                          + outputfile

                with open(outputfile, "a") as f:
                    f.write("\nCommand seed: %s\n"%i)
                print "Executing: ", command
                Test(command).start()

                with open(outputfile, "a") as f:
                    f.write("\n============================================\n")

if __name__ == '__main__':
    main(sys.argv[1:])
    
