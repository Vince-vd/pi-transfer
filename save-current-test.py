from interruptingcow import timeout  #interruptingcow needs to be installed using pip (enter 'pip install interruptingcow' in terminal)
import time
from datetime import datetime
from roboclaw import Roboclaw

sampletime = 5         #sampletime in seconds

rc = Roboclaw("/dev/ttyACM0",460800)
rc.Open()
address = 0x80

print "starting motor"
rc.ForwardM1(address,64) # run at half power
time.sleep(1) #sleep for 1 second to let motor ramp up

data = []

'''Sample current data as fast as possible for 5 seconds. Save data and print afterwards'''

print "sampling data for" + str(sampletime) + " seconds"
from interruptingcow import timeout
try:
    with timeout(sampletime, exception=RuntimeError):
        while True:
            current = rc.ReadCurrents(address)
            time = str(datetime.now())
            data.append([time,current[1],current[2]])
except RuntimeError:
    pass

rc.ForwardM1(address,0) # stop motor
print "sampling complete, saving data"

f = open('currentData.csv','w')
f.write('Time,M1 Current[A],M2 Current[A]\n')

i=1

for r in data:
    curr1 = r[1]/100.0
    curr2 = r[2]/100.0
    print str(i) + " | Time: " + str(r[0]) + " | Motor 1 current[A]: " + str(curr1) + " | Motor 2 current[A]: " + str(curr2) + "\n"
    f.write(str(r[0]) + ',' + str(curr1) + ',' + str(curr2) + "\n" )
    i+=1

f.close()

print "Operatoin complete, recorded " + str(i) + " samples in " + str(sampletime) + " seconds\n this means " + str(i/sampletime) + " samples per second" 
