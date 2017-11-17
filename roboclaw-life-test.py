import time
from roboclaw import Roboclaw
from interruptingcow import timeout
import logging, sys
from datetime import datetime
import os


'''
sample current for a certain amount of time in seconds.
saves current in queue
'''
def sampleCurrent(sampleTime):
    currRead = []
    try:
        logging.debug("starting current sampling")
        with timeout(sampleTime, exception=RuntimeError):
            while True:                             # execute the following code block until timeout
                curr = rc.ReadCurrents(address)     # Read current from roboclaw
                readTime = str(datetime.now())          # get current time to idenitify reading
                currRead.append([readTime,curr[1],curr[2]])
    except RuntimeError:
        pass
    logging.debug("Sampling done")
    return currRead


'''
Function to print current value and save
The "readings" variable should be a list,
each list element is another list of the form [time,curent,power] where current is the current object returned by roboclaw
'''
def printSaveCurrent(testNum, testVolt, readings):

    # open csv file where current readings will be saved.
    # TODO: Better coding would be to make this a try statement and check if the file can actually be opened
    logging.debug('creating file in directory ' + str(filePath))
    fName = 'test-%s.csv' % (str(testNum))
    f = open(filePath + fName,'w')
    f.write('Time,Test,Voltage [V],M1 Current[A],M2 Current[A]\n') # write headers to file
    #for each reading in the list readings print a line to the csv file to save that reading's info
    logging.debug("saving current readings")

    for reading in readings:
        readTime  = reading[0]
        curr1 = str(reading[1]/100.0)
        curr2 = str(reading[2]/100.0)
        # write readings to new line in csv file
        f.write('%s,%s,%s,%s,%s\n' % (readTime,str(testNum),str(testVolt),curr1,curr2) )

        ## Uncomment print for debugging print
        #logging.debug('Time: %s \n\tVoltage [V]:%s \n\tM1 Current [A]: %s \n\tM2 Current [A]:%s' % (time,power,curr1,curr2))
    logging.debug("saving done")
    f.close()
    logging.debug("file closed")

'''
This function runs the motors forward for a given amount of time in seconds at a given voltage in volts.
It saves voltage, current and time during the operatoin and rests 60 seconds afterwards
'''
def testRun(testNum, volt, testTime):
    # recheck voltage, make sure it's still high enough
    readVolt = rc.ReadMainBatteryVoltage(address)
    VS = readVolt[1]/10.0
    if VS < minVolt:
        logging.info("Test paused, supply voltage is too low, must be at least %s. \n Please increase input voltage to resume." % (str(minVolt)))
        logging.debug("Voltage is " + str(VS))
        # Continously read voltage every second. Don't continue until voltage is high enough
        while VS < minVolt:
            time.sleep(1)
            readVolt = rc.ReadMainBatteryVoltage(address)
            VS = readVolt[1]/10.0
        logging.info("Input voltage sufficient, test is resuming")
        logging.debug("Input voltage is " + str(VS))


    # initiate list of readings
    readings = []
    power = (volt/VS) * 127.0
    power = int(round(power))
    # Make sure power setting doesn't exceed 127 or go below 0
    if power > 127:
        power = 127
    elif power < 0:
        power = 0
    logging.debug('running test %s, chosen power setting is %s ' % (testNum,str(power)))

    # Sample current before running motors
    # Extend current list of readings with list returned by the sampleCurrent function
    readings.extend(sampleCurrent(leadTime))
    # Run motors
    rc.ForwardM1(address,power)	#1/4 power forward
    rc.ForwardM2(address,power)	#1/4 power forward
    # Sample current while motors are running
    # Extend current list of readings with list returned by the sampleCurrent function
    readings.extend(sampleCurrent(testTime))
    # Stop motors
    rc.ForwardM1(address,0)
    rc.ForwardM2(address,0)
    # Sample current after test
    # Extend current list of readings with list returned by the sampleCurrent function
    readings.extend(sampleCurrent(leadTime))
    # save current readings and cooldown
    printSaveCurrent(testNum,volt,readings)
    time.sleep(cooldown)

    logging.info('completed %s tests' % (testNum))



'''
MAIN PROGRAM
'''

logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)         # enable logging

#Windows comport name
#rc = Roboclaw("COM9",115200)
#Linux comport name'''
rc = Roboclaw("/dev/ttyACM0",115200)

rc.Open()

address = 0x80


#############################################
#           TO BE SET BY TESTER             #
#############################################
##################################################################################
leadTime = 3 # time to sample current before and after test
cooldown = 5 # cooldown time in seconds
desiredVolt = [6,9,12] # list of voltages to use for test
numTests = 9
###################################################################################
# TODO: create directory per test
# TODO: one csv file per test

# Read voltage, value can be used to calculate the power needed for each voltage setting
# Throw error if Voltage is lower than highest voltage in voltage list
minVolt = max(desiredVolt)  # store minimum required voltage
readVolt = rc.ReadMainBatteryVoltage(address)
VS = readVolt[1]/10.0
if VS < minVolt:
    logging.error("Supply voltage is too low, must be at least %s please increase voltage and rerun test." % (minVolt))
    logging.debug("exiting program early due to low supply voltage")
    sys.exit()
power = 0.0   #global power value to use when saving current readings

#Create directory for current test, used to save all the csv file for this test.
startTime = datetime.now()
startTime = startTime.replace(microsecond=0)
dirName = "test-" + str(startTime)
filePath = "/tests/" + dirName + "/"
directory = os.path.dirname(filePath)

# Check if test directory already exists (it shouldn't) and create it if it doesn't.
if not os.path.exists(directory):
    os.makedirs(directory)


i=1
while(i < (numTests + 1) ):

    # run at all voltages for 0.10s
    logging.debug("running tests for 0.10s")
    for voltage in desiredVolt:
        testRun(i,voltage,0.10)
        i+=1

    # run at all voltages for 0.5s
    logging.debug("running tests for 0.50s")
    for voltage in desiredVolt:
        testRun(i,voltage,0.5)
        i+=1

    # run at all voltages for 1.5s
    logging.debug("running tests for 1.50s")
    for voltage in desiredVolt:
        testRun(i,voltage,1.5)
        i+=1

logging.debug("test completed, file closed")
logging.info("Test completed succesfully, test results can be found in the following location: " + directory)
