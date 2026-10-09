#!/usr/bin/env python3

'''
	Author Jacob A. Psimos
	
	Creates and manages a 'router.py' instance.
'''

import os
import sys
import json
import subprocess
import syslog
import signal
import time
import traceback
import helpers
from router import Router

# Definitions
EXIT_SUCCESS = 0
EXIT_FAIL = 1
COMMAND_NONE = 0
COMMAND_STOP = -1
COMMAND_START = -2
COMMAND_RESTART = -3
COMMAND_RELOAD = -4

# Globals
receivedSigQuit = False

# Code
def Main():
	exitValue = EXIT_SUCCESS
	configFilePath = None
	command = None
	noBridges = None
	noDnsmasq = None
	noHostapd = None
	routerInstance = None
	
	syslog.openlog(ident = 'router ' + os.path.basename(sys.argv[0]) + ': ', logoption=syslog.LOG_PID | syslog.LOG_PERROR, facility=syslog.LOG_LOCAL0)
	signal.signal(signal.SIGQUIT, SignalHandler)
	
	try:
		configFilePath, command, noBridges, noDnsmasq, noHostapd = ParseArguments()
		routerInstance = Router(configFilePath, noBridges, noDnsmasq, noHostapd)

	except Exception as initializationException:
		exitValue = EXIT_FAIL
		command = COMMAND_NONE
		syslog.syslog(syslog.LOG_ERR, f'{__file__}:{sys._getframe().f_lineno} Initialization error: {initializationException}' + "\n" + traceback.format_exc())
	
	try:
		if command == COMMAND_START:
			routerInstance.Start()
			
		elif command == COMMAND_STOP:
			routerInstance.Stop()
			
		elif command == COMMAND_RESTART:
			routerInstance.Restart()
			
		elif command == COMMAND_RELOAD:
			routerInstance.Reload()
			
		while not receivedSigQuit:
			break
			
	except Exception as runtimeException:
		exitValue = EXIT_FAIL
		syslog.syslog(syslog.LOG_ERR, f'{__file__}:{sys._getframe().f_lineno} Command error: {runtimeException}' + "\n" + traceback.format_exc())

	syslog.closelog()
	
	return exitValue
	
def SignalHandler(signum, frame):
	if signum == signal.SIGQUIT:
		receivedSigQuit = True
		
	print('Signal handler called with signal', signum)

def PrintHelp(exitCode = None):
	print('linux router service')
	print(f'{sys.argv[0]} [options] args...')
	print()
	print(' --help           -h          Show this help message.')
	print(' --config         -c          Use provided config file.')
	print(' --stop           -S          Stop the router service.')
	print(' --start          -s          Start the router service.')
	print(' --restart        -r          Restart the router service.')
	print(' --reload         -R          Reload the router service.')
	print(' --no-dnsmasq     -D          Do not configure dnsmasq instance(s.)')
	print(' --no-hostapd     -H          Do not configure hostapd instance(s.)')
	print(' --no-bridge      -B          Do not configure bridge(s.)')
	print()
	print('Author Jacob A. Psimos')
	
	if exitCode is not None:
		sys.exit(exitCode)

def ParseArguments():
	configFile = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'config.json')
	command = COMMAND_NONE
	noBridges = False
	noDnsmasq = False
	noHostapd = False
	
	if len(sys.argv) == 1:
		PrintHelp(exitCode = 1)
	
	for argi in range(1, len(sys.argv)):
		arg = sys.argv[argi]
		nextArg = sys.argv[argi + 1] if argi + 1 < len(sys.argv) else None

		if arg == '--help' or arg == '-h':
			PrintHelp(exitCode = 0)

		elif arg == '--config' or arg == '-c':
			configFile = nextArg
			
		elif arg == '--stop' or arg == '-S':
			command = COMMAND_STOP
			
		elif arg == '--start' or arg == '-s':
			command = COMMAND_START
			
		elif arg == '--restart' or arg == '-r':
			command = COMMAND_RESTART
			
		elif arg == '--reload' or arg == '-R':
			command = COMMAND_RELOAD
			
		elif arg == '--no-bridges' or arg == '-B':
			noBridges = True
			
		elif arg == '--no-dnsmasq' or arg == '-D':
			noDnsmasq = True
			
		elif arg == '--no-hostapd' or arg == '-H':
			noHostapd = True

	return configFile, command, noBridges, noDnsmasq, noHostapd

if __name__ == '__main__':
	sys.exit(Main())
