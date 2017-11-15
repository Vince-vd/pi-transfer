from interruptingcow import timeout  #interruptingcow needs to be installed using pip (enter 'pip install interruptingcow' in terminal)
import time
from datetime import datetime
from roboclaw import Roboclaw

sampletime = 5         #sampletime in seconds

rc = Roboclaw("/dev/ttyACM0",115200)
rc.Open()
address = 0x80

print "starting motor"
rc.ForwardM1(address,64) # run at half power
time.sleep(1) #sleep for 1 second to let motor ramp up

data = List()

'''Sample current data as fast as possible for 5 seconds. Save data and print afterwards'''

print "sampling data for" + sampletime " seconds"
from interruptingcow import timeout
try:
    with timeout(sampletime, exception=RuntimeError):
        while True:
            current = ReadCurrents(address)
            time = str(datetime.now())
            data.append([time,str(current[1]),str(current[2])])
except RuntimeError:
    pass

print "sampling complete, saving data"

f = open('currentData.csv','w')
f.write('Time,M1 Current[A],M2 Current[A]\n')

i=1

for r in data:
    print i + " | Time: " + r[0] + " | Motor 1 current[A]: " + r[1]/100 + " | Motor 2 current[A]: " + r[2]/100 + "\n"
    f.write(r[0] + ',' + r[1]/100 + ',' + r[2]/100)
    i++

f.close()

print "Operatoin complete, recorded " + i " samples in " + sampletime + " seconds"
