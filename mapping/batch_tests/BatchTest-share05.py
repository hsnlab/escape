import subprocess

if __name__ == '__main__':
    commbatch = "python ../StressTest.py --bw_factor=1.0 --lat_factor=1.0 --res_factor=1.0 --vnf_sharing=0.05 --vnf_sharing_same_sg=0.0 --shareable_sg_count=4 --batch_length=4 --request_seed="

    for i in xrange(0,500):
        command = commbatch + str(i) + " 2>> share05.out"

        with open("share05.out", "a") as f:
            f.write("\nCommand seed: %s\n"%i)

        subprocess.call(command, shell=True)

        with open("share05.out", "a") as f:
            f.write("\n============================================\n")

