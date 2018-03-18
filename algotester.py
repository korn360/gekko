#!/usr/bin/python

#
# Recursive Tester
#	Created by Justin McCormick
#	(minivan)
#

import subprocess
from datetime import datetime
import re
import sys
import signal

import os, time
from subprocess import Popen, list2cmdline


#################################################################################
#Changes from here

python_path = 'C:\Users\jabba\.windows-build-tools\python27\python.exe'

# Do we have variables in "XXX: { A:,0, B: 1}," then add "XXX:" here and uncomment the "}," in the configbk-template.js.
Header = '';

# Name of your strategy
algoname = "mvpscalper"

# How many tasks we can run in parallel on this CPU
max_task = 4


# One line per candleSize you want to test
commands = [

	# Candle size is first parameter
	# Second parameter is one of the settings for the strategy that we want to parallelize on
	# The LAST one in this list is calculated first. So place the faster (longer candle size) or the ones you assume is better in the end of the list
    [python_path,'algotester.py', '10', 'time', '1'],
    [python_path,'algotester.py', '10', 'time', '5'],
    [python_path,'algotester.py', '10', 'time', '10'],
]

variables = {
    # 'time' : [1,5,10],
    'short' : [5,6,7,8,9,10,11,12,13,14,15],
    'long' : [20,21,22,23,24,25,26,27,28,29,30,31,32,33,34],
    'stop' : [0.96,0.97,0.98,0.99],
    'take' : [1.01,1.02,1.03,1.04,1.05],
}

#Changes until here
#################################################################################



# OLD !!!
# with : recurse_candles('ma_trend: { ', 0)
# you can run it all in one process instead of parallel as I am doing it now.
candlesizes = {
	# 'candleSize' : [60,55,50,45,40,30,20,10,5,1]
	# 'candleSize' : [60,55,50,45,40,30,20]
	'candleSize' : [10]
}


# Stores Output
results = {}

# Needed for Recursiveness
keys = variables.keys()
vals = variables.values()
candlekeys = candlesizes.keys()
candlevals = candlesizes.values()




def sig_handler(signal, frame):
    print('[-] Exiting due to Ctrl-C')
    sys.exit(0)

def call_process(strtorun, candlesize):
    processtorun = 'node gekko.js -b -c config-backtest-temp-'+candlesize+'.js'
    result = subprocess.check_output(processtorun.split())
    # Search for Percentage & Win/Loss
    m = re.search('.*simulated profit\:.*\((.*)\%\)', result)
    if m: percent = m.group(1)
    # Sharpe Ratio
    m = re.search('.*sharpe ratio:[\s]*(.*)', result)
    if m: ratio = m.group(1)

    # Store into table as Percentage Key
    try:
        results[percent] = '{}'.format(percent)
        line = "\t" + str(percent)
        print(line)

        fh = open(filename,"a")
        fh.write('candleSize: '+candlesize + " / " + strtorun + line + "\n")
        fh.close()
    except:
        print('Variable Not Defined')

def recurse_combos(strtorun, candlesize, k_ind):
    for item in vals[k_ind]:
        # Replace Key=Value if there is already one
        pat = re.compile('{}: '.format(keys[k_ind]))
        if pat.search(strtorun):
            strtorun = re.sub('({}: [^\s]+)'.format(keys[k_ind]), '{}: {},'.format(keys[k_ind], item), strtorun)
        else:
            strtorun = strtorun + ' {}: {},'.format(keys[k_ind], item)

        if k_ind < (len(keys) - 1):
            recurse_combos(strtorun, candlesize, k_ind + 1) # Next Item In Variables
        else:
            # Format Process to Run String
            # processtorun = 'node gekko.js -b -c config.js'
            # linetoreplace = ('config.%s = { ' % algoname) + strtorun + ' };'
            linetoreplace = ('config.%s = { ' % algoname) + strtorun + ' },'
            print('candleSize: '+candlesize+' / '+linetoreplace)
            with open('config-backtest-temp-candle-'+candlesize+'.js', 'r') as input_file, open('config-backtest-temp-'+candlesize+'.js', 'w') as output_file:
                for line in input_file:
                    if ('config.%s' % algoname) in line.strip():
                        output_file.write(linetoreplace)
                    else:
                        output_file.write(line)

            # Run Process Here
            call_process(linetoreplace, candlesize)

def set_candleSize_in_config(candlesize):

		# Format Process to Run String
		strtoreplace = ' {}: {},'.format('candleSize', candlesize)
		linetoreplace = ('  ' + strtoreplace)
		# print(linetoreplace)
		with open('configbk-template.js', 'r') as input_file, open('config-backtest-temp-candle-'+candlesize+'.js', 'w') as output_file:
			for line in input_file:
				if ('candleSize: <CANDLE-SIZE>') in line.strip():
					output_file.write(linetoreplace)
				else:
					output_file.write(line)

def Remove_temp_config(candlesize):
	print "Removing temporary config files again."
	os.remove('config-backtest-temp-candle-'+candlesize+'.js')
	os.remove('config-backtest-temp-'+candlesize+'.js')

def recurse_candles(strtorun, c_ind):
    for item in candlevals[c_ind]:

		# Format Process to Run String
		strtoreplace = ' {}: {},'.format(candlekeys[c_ind], item)
		linetoreplace = ('  ' + strtoreplace)
		# print(linetoreplace)
		with open('configbk-template.js', 'r') as input_file, open('config-backtest-temp-candle-'+candlesize+'.js', 'w') as output_file:
			for line in input_file:
				if ('candleSize: <CANDLE-SIZE>') in line.strip():
					output_file.write(linetoreplace)
				else:
					output_file.write(line)

		# run all variables
		recurse_combos(strtorun, linetoreplace, 0)
		sort_results()

			
def sort_results():
    print("\n[+] Printing Sorted Results\n")
    keylist = results.keys()
    keylist.sort()

    fh = open(filename,"a")
    fh.write("\n\n- Sorted results:\n")
    for key in keylist:
        line = '{}'.format(results[key])
        print(line)
        fh.write(line + "\n")
    fh.close()
    print("\n[-] Wrote Results to "+filename)

def exec_commands(cmds):
    ''' Exec commands in parallel in multiple process 
    (as much as we have CPU)
    '''
    if not cmds: return # empty list

    def done(p):
        return p.poll() is not None
    def success(p):
        return p.returncode == 0
    def fail():
        sys.exit(1)


    processes = []
    while True:
        while cmds and len(processes) < max_task:
            task = cmds.pop()
            print task
            # print list2cmdline(task)
            processes.append(Popen(task))

        for p in processes:
            if done(p):
                if success(p):
                    processes.remove(p)
                else:
                    fail()

        if not processes and not cmds:
            break
        else:
            time.sleep(0.05)

def Handle_test(candlesize,StratVar,StratVal):

	signal.signal(signal.SIGINT, sig_handler)
	fh = open(filename,"w")
	fh.close()

	print('[+] Beginning Algorithm Tester, candleSize '+candlesize+': {}'.format(str(datetime.now())))
	if not StratVar: 
		recurse_combos(Header,candlesize, 0)
	else:
		recurse_combos(Header+StratVar+': '+StratVal+', ',candlesize, 0)
	sort_results()
	# recurse_candles('ma_trend: { ', 0)
	print('[+] Ended Algorithm Tester, candleSize '+candlesize+': {}'.format(str(datetime.now())))

	
if __name__ == "__main__":
	# First argument is Candle size. If empty, start all processes
	if len(sys.argv) > 1:
		filename = "results"+sys.argv[1]+"-"+sys.argv[2]+"_"+sys.argv[3]+".txt"
		set_candleSize_in_config(sys.argv[1])
		Handle_test(sys.argv[1],sys.argv[2],sys.argv[3])
		# Clean up temprary config files
		Remove_temp_config(sys.argv[1])
	else:
		exec_commands(commands)
