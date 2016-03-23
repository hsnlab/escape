import subprocess

# NOTE:Sliding without sharing does nothing... 
# (it is the same test as BatchTest-batched.py)

if __name__ == '__main__':
    commbatch = "python ../StressTest.py --bw_factor=1.0 --lat_factor=1.0 --res_factor=1.0 --vnf_sharing=0.0 --vnf_sharing_same_sg=0.0 --sliding_share --shareable_sg_count=4 --batch_length=4 --request_seed="

    for i in xrange(0,100):
        batched = commbatch + str(i) + " 2>> sliding-4batched.out"

        with open("sliding-4batched.out", "a") as batch:
            batch.write("\nCommand seed: %s\n"%i)

        subprocess.call(batched, shell=True)

        with open("sliding-4batched.out", "a") as batch:
            batch.write("\n============================================\n")

