import subprocess

if __name__ == '__main__':
    commbatch = "python ../StressTest.py --bw_factor=1.0 --lat_factor=1.0 --res_factor=1.0 --vnf_sharing=0.0 --vnf_sharing_same_sg=0.0 --shareable_sg_count=4 --batch_length=8 --request_seed="

    for i in xrange(0,500):
        batched = commbatch + str(i) + " 2>> 8batched.out"

        with open("8batched.out", "a") as batch:
            batch.write("\nCommand seed: %s\n"%i)

        subprocess.call(batched, shell=True)

        with open("8batched.out", "a") as batch:
            batch.write("\n============================================\n")

