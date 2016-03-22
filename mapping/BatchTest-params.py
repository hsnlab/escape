import subprocess, getopt, sys

helpmsg="""
Script to give start and give parameters to BatchTests.

   --stress_type=<<agressive|normal|decent>>   The name of the available 
                                               StressTest-*.py script to be used.
   --seed_start=i          The starting seed for the test sequences
   --seed_end=i            The end seed for the test sequences
   --t                     If set, time is measured for each StressTest.
   --batch_length=i        The number of SG-s to batch together.
   --bt_limit=i            Backtracking depth limit of mapping.
   --bt_br_factor=i        Branching factor of bactracking of mapping.
"""

def main(argv):
    try:
        opts, args = getopt.getopt(argv,"ht",["stress_type=", "seed_start=", 
                                              "seed_end=", "batch_length=", 
                                              "bt_limit=", "bt_br_factor="])
    except getopt.GetoptError as goe:
        print helpmsg
        raise
    stress_type = None
    seed_start = 0
    seed_end = 10
    time = False
    batch_length = 1
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
            batch_length = int(arg)
        elif opt == "--bt_limit":
            bt_limit = int(arg)
        elif opt == "--bt_br_factor":
            bt_br_factor = int(arg)

    if stress_type is None:
        print "StressTest type must be given!"
        print helpmsg
        sys.exit()

    outputfile = "batch_tests/%s-%sbatched-seed%s-%s-bt%s-%s.out"\
                 %(stress_type, batch_length, seed_start, seed_end, bt_limit, 
                   bt_br_factor)
    commtime = "/usr/bin/time -o "+outputfile+" -a -f \"%U user,\t%S sys,\t%E real\" "
    commbatch = "python StressTest-%s.py --bw_factor=0.5 --lat_factor=2.0 --res_factor=0.5 --vnf_sharing=0.0 --vnf_sharing_same_sg=0.0 --shareable_sg_count=4 --batch_length=%s --bt_limit=%s --bt_br_factor=%s --request_seed="%(stress_type, batch_length, bt_limit, bt_br_factor)
    if time:
        commbatch = commtime + commbatch
    for i in xrange(seed_start,seed_end):
        command = commbatch + str(i) + " 2>> " + outputfile
        
        with open(outputfile, "a") as f:
            f.write("\nCommand seed: %s\n"%i)
            
        subprocess.call(command, shell=True)

        with open(outputfile, "a") as f:
            f.write("\n============================================\n")

if __name__ == '__main__':
    main(sys.argv[1:])
    
