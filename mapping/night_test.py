import threading, os

semaphore = threading.Semaphore(8)

class Test(threading.Thread):
    
    def __init__(self, command):
        threading.Thread.__init__(self)
        self.command = command

    def run(self):
        semaphore.acquire()
        os.system(self.command)
        semaphore.release()


Test("python BatchTest-params.py --stress_type=decent --seed_start=0 --seed_end=220 -t --batch_length=1 --bt_limit=6 --bt_br_factor=3").start()

Test("python BatchTest-params.py --stress_type=decent --seed_start=0 --seed_end=220 -t --batch_length=4 --bt_limit=6 --bt_br_factor=3").start()

Test("python BatchTest-params.py --stress_type=decent --seed_start=0 --seed_end=220 -t --batch_length=4 --bt_limit=12 --bt_br_factor=2").start()

Test("python BatchTest-params.py --stress_type=decent --seed_start=0 --seed_end=220 -t --batch_length=4 --bt_limit=7 --bt_br_factor=3").start()

Test("python BatchTest-params.py --stress_type=decent --seed_start=0 --seed_end=220 -t --batch_length=4 --bt_limit=8 --bt_br_factor=2").start()

Test("python BatchTest-params.py --stress_type=decent --seed_start=0 --seed_end=220 -t --batch_length=2 --bt_limit=6 --bt_br_factor=3").start()

Test("python BatchTest-params.py --stress_type=decent --seed_start=0 --seed_end=220 -t --batch_length=2 --bt_limit=12 --bt_br_factor=2").start()

#=====================================

Test("python BatchTest-params.py --stress_type=sharing --seed_start=0 --seed_end=220 -t --batch_length=1 --bt_limit=6 --bt_br_factor=3").start()

Test("python BatchTest-params.py --stress_type=sharing --seed_start=0 --seed_end=220 -t --batch_length=4 --bt_limit=12 --bt_br_factor=2").start()

Test("python BatchTest-params.py --stress_type=sharing --seed_start=0 --seed_end=220 -t --batch_length=4 --bt_limit=8 --bt_br_factor=3").start()

Test("python BatchTest-params.py --stress_type=sharing --seed_start=0 --seed_end=220 -t --batch_length=4 --bt_limit=6 --bt_br_factor=3").start()

#=====================================

Test("python BatchTest-params.py --stress_type=agressive --seed_start=0 --seed_end=220 -t --batch_length=1 --bt_limit=6 --bt_br_factor=3").start()

Test("python BatchTest-params.py --stress_type=agressive --seed_start=0 --seed_end=220 -t --batch_length=4 --bt_limit=6 --bt_br_factor=3").start()

Test("python BatchTest-params.py --stress_type=agressive --seed_start=0 --seed_end=220 -t --batch_length=4 --bt_limit=8 --bt_br_factor=3").start()

Test("python BatchTest-params.py --stress_type=agressive --seed_start=0 --seed_end=220 -t --batch_length=4 --bt_limit=12 --bt_br_factor=2").start()

#==========================================

Test("python BatchTest-params.py --stress_type=normal --seed_start=0 --seed_end=220 -t --batch_length=1 --bt_limit=6 --bt_br_factor=3").start()

Test("python BatchTest-params.py --stress_type=normal --seed_start=0 --seed_end=220 -t --batch_length=4 --bt_limit=6 --bt_br_factor=3").start()

Test("python BatchTest-params.py --stress_type=normal --seed_start=0 --seed_end=220 -t --batch_length=4 --bt_limit=12 --bt_br_factor=2").start()

# ======================================

Test("python BatchTest-params.py --stress_type=sc8decent --seed_start=0 --seed_end=220 -t --batch_length=1 --bt_limit=6 --bt_br_factor=3").start()

Test("python BatchTest-params.py --stress_type=sc8decent --seed_start=0 --seed_end=220 -t --batch_length=4 --bt_limit=6 --bt_br_factor=3").start()

Test("python BatchTest-params.py --stress_type=sc8decent --seed_start=0 --seed_end=220 -t --batch_length=4 --bt_limit=12 --bt_br_factor=2").start()

#=========================================
