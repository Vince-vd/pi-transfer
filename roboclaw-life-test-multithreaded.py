import threading
import time
from roboclaw import Roboclaw
import Queue
import logging, sys
from datetime import datetime
import random

q = Queue.Queue()

maxVolt = 0.0
leadTime = 2
restTime = 5                   # resttime in seconds
power = 0                       # global power value to use when saving current readings

logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)         # enable logging

'''
Producer thread reads current as fast as possible and saves it to queue to be processed by consumer
'''
class readCurrentThread(threading.Thread):
    def __init__(self, group=None, target=None, name=None,
                 args=(), kwargs=None, verbose=None):
        super(readCurrentThread,self).__init__()
        self.target = target
        self.name = name
        self.paused = False
        self.running = True         # Provide variable usable to stop Producer
        # Explicitly using Lock over RLock since the use of self.paused
        # break reentrancy anyway, and I believe using Lock could allow
        # one thread to pause the worker, while another resumes; haven't
        # checked if Condition imposes additional limitations that would
        # prevent that. In Python 2, use of Lock instead of RLock also
        # boosts performance.
        self.pause_cond = threading.Condition(threading.Lock())

    def run(self):
        logging.info('Started producer thread, reading current')
        while self.running:
            # Wait for resume statement if thread is paused
            with self.pause_cond:
                while self.paused:
                    logging.debug('producer paused')
                    self.pause_cond.wait()
            # Execute the code below if not paused
            if not q.full():
                curr = rc.ReadCurrents(address)
                readTime = str(datetime.now())
                q.put([readTime,curr,power])
                #logging.debug('Putting ' + str(curr)
                #              + ' : ' + str(q.qsize()) + ' items in queue')
            time.sleep(0.01)

        q.put(None) # Add "None" to queueue when stopping so consumer can be easily stopped.
        return

    def pause(self):
        logging.debug('pausing producer')
        self.paused = True
        # If in sleep, we acquire immediately, otherwise we wait for thread
        # to release condition. In race, worker will still see self.paused
        # and begin waiting until it's set back to False
        self.pause_cond.acquire()

    #should just resume the thread
    def resume(self):
        self.paused = False
        # Notify so thread will wake after lock released
        self.pause_cond.notify()
        # Now release the lock
        self.pause_cond.release()
        logging.debug('resuming producer')

    # Should stop producer
    def stop(self):
        logging.debug('stopping producer')
        self.paused = False
        # Give producer stop signal once we resume
        self.running = False
        # Notify so thread will wake after lock released
        self.pause_cond.notify()
        # Now release the lock
        self.pause_cond.release()

'''
Consumer thread reads current from queueu prodced by producer and saves current with timestamp to csv file.
'''
class saveCurrentThread(threading.Thread):

    def __init__(self, group=None, target=None, name=None,
                 args=(), kwargs=None, verbose=None):
        super(saveCurrentThread,self).__init__()
        self.target = target
        self.name = name
        self.f = open('currentData.csv','w')
        self.f.write('Time,Voltage [V],M1 Current[A],M2 Current[A]\n')
        return

    def run(self):
        while True:
            if not q.empty():
                reading = q.get()
                if reading is None:
                    logging.debug('closing file')
                    self.f.close()
                    logging.debug('stopping consumer')
                    break
                #logging.debug('Getting ' + str(reading)
                #              + ' : ' + str(q.qsize()) + ' items in queue')
                # TODO: send correct variables to saveData() function
                self.saveData(reading)
            else:
                time.sleep(random.random())
        return

    '''Save current data, time and voltage test was run at to csv file'''
    # TODO: voltage needs to be saved as well
    def saveData(self, data):
        readTime = data[0]
        curr = data[1]
        power = str(data[2])
        curr1 = str(curr[1])                                    #extract current from current object and convert to string
        curr2 = str(curr[2])
        self.f.write(readTime + ',' + power + ',' + curr1 + ',' + curr2 + '\n')


'''
This function runs the motors forward for a given amount of time in seconds at a given voltage in volts.
It saves voltage, current and time during the operatoin and rests 60 seconds afterwards
'''
def testRun(volt, runTime):

    power = (volt/maxVolt) * 127.0
    power = int(round(power))
    logging.debug('power before safety check: ' + str(power))
    # Make sure power setting doesn't exceed 127 or go below 0
    if power > 127:
        power = 127
    elif power < 0:
        power = 0
    logging.debug('chosen power setting is ' + str(power))
    # Resume producer, this will save current before, during and after test
    r.resume()
    # Wait for a chosen amount of time, gather current data before test starts as a reference
    time.sleep(leadTime)
    # Run motors forward
    m1Write = rc.ForwardM1(address,power)	#1/4 power forward
    m2Write = rc.ForwardM2(address,power)	#1/4 power forward
    logging.debug('starting m1 write result = ' + str(m1Write))
    logging.debug('starting m2 write result = ' + str(m2Write))
    # wait for chosen amount of time before turning of the motors again
    time.sleep(runTime)
    m1Write = rc.ForwardM1(address,0)
    m2Write = rc.ForwardM2(address,0)
    logging.debug('stopping m1 write result = ' + str(m1Write))
    logging.debug('stopping m2 write result = ' + str(m2Write))

    # Again wait for chosen amount of time to gather current after turning motors of to use as reference
    time.sleep(leadTime)

    # pause producer during cooldown. Don't need to save current
    r.pause()

    # Wait to let system cool down
    time.sleep(restTime)



'''
main function
creates consumer and producer threadName
runs test, will run motor 9000 times in total
'''
if __name__ == '__main__':
    rc = Roboclaw("/dev/ttyACM0",115200)

    rc.Open()
    address=0x80

    readVolt = rc.ReadMainBatteryVoltage(address)
    maxVolt = readVolt[1]/10
    logging.info('set max voltage to ' + str(maxVolt))

    r = readCurrentThread(name='readCurrent')
    s = saveCurrentThread(name='saveCurrent')

    s.start()
    r.start()
    r.pause()

    i = 0
    while(i < 9 ):

        testRun(6.0, 0.1)
        i+=1
        logging.debug('ran test ' + str(i))
        testRun(9.0, 0.1)
        i+=1
        logging.debug('ran test ' + str(i))
        testRun(12.0, 0.1)
        i+=1
        logging.debug('ran test ' + str(i))

        testRun(6.0, 0.5)
        i+=1
        logging.debug('ran test ' + str(i))
        testRun(9.0, 0.5)
        i+=1
        logging.debug('ran test ' + str(i))
        testRun(12.0, 0.5)
        i+=1
        logging.debug('ran test ' + str(i))

        testRun(6.0, 1.5)
        i+=1
        logging.debug('ran test ' + str(i))
        testRun(9.0, 1.5)
        i+=1
        logging.debug('ran test ' + str(i))
        testRun(12.0, 1.5)
        i+=1
        logging.debug('ran test ' + str(i))


    # stop and join producer when loop ends
    r.stop()
    r.join()
    logging.info('producer stopped and joined')
    # stop and join consumer thread after producer is stopped
    s.join()
    logging.info('consumer stopped and joined. Thank you for using this program')
    rc.ForwardM1(address,0)
    rc.ForwardM2(address,0)
    logging.debug('sent stop signal to motors for good measure')
