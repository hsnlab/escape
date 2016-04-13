import subprocess

if __name__ == '__main__':
    commbatch = "python ../StressTest.py --bw_factor=1.0 --lat_factor=1.0 --res_factor=1.0 --vnf_sharing=0.0 --vnf_sharing_same_sg=0.0 --shareable_sg_count=4 --batch_length=4 --request_seed="
    commnonbatch = "python ../StressTest.py --bw_factor=1.0 --lat_factor=1.0 --res_factor=1.0 --vnf_sharing=0.0 --vnf_sharing_same_sg=0.0 --shareable_sg_count=4 --batch_length=1 --request_seed="

    for i in xrange(0,1500):
        batched = commbatch + str(i) + " 2>> batched.out"

        with open("batched.out", "a") as batch:
            batch.write("\nCommand seed: %s\n"%i)

        subprocess.call(batched, shell=True)

        with open("batched.out", "a") as batch:
            batch.write("\n============================================\n")

