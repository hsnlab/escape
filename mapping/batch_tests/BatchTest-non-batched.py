import subprocess

if __name__ == '__main__':
    commbatch = "python StressTest.py --bw_factor=1.0 --lat_factor=1.0 --res_factor=1.0 --vnf_sharing=0.0 --vnf_sharing_same_sg=0.0 --shareable_sg_count=4 --batch_length=4 --request_seed="
    commnonbatch = "python StressTest.py --bw_factor=1.0 --lat_factor=1.0 --res_factor=1.0 --vnf_sharing=0.0 --vnf_sharing_same_sg=0.0 --shareable_sg_count=4 --batch_length=1 --request_seed="
    
    for i in xrange(0,1500):
        nonbatched = commnonbatch + str(i) + " 2>> non-batched.out"

        with open("non-batched.out", "a") as nbatch:
            nbatch.write("\nCommand seed: %s\n"%i)

        subprocess.call(nonbatched, shell=True)

        with open("non-batched.out", "a") as nbatch:
            nbatch.write("\n============================================\n")

