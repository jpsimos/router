#!/usr/bin/env python3

'''
	Author Jacob A. Psimos
	
	Utility to interact with configured hostapd instances.
'''

import sys
import os
import sys
import json
import subprocess
import threading
import random
import signal
import time
import helpers

# Globals
receivedSigQuit = False

def SignalHandler(signum, frame):
	global receivedSigQuit
	if signum == signal.SIGQUIT or signum == signal.SIGINT:
		receivedSigQuit = True

def PrintHelp(exitCode = None):
	print('linux router wifi')
	print(f'{sys.argv[0]} [options] [command] args...')
	print()
	print(' --help           -h          Show this help message.')
	print(' --config         -c          Use provided config file.')
	print(' --interface      -i          Use specific interface name.')
	print()
	print('Commands')
	print(' stas             Show STAs.')
	print(' signal           Show STA signals.')
	print(' monitor          Periodically monitor STA signal (each second.)')
	print('Author Jacob A. Psimos')
	
	if exitCode is not None:
		sys.exit(exitCode)

def ParseArguments():
	command = None
	interface = None
	configFile = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'config.json')
	
	if len(sys.argv) == 1:
		PrintHelp(exitCode = 1)
	
	for argi in range(1, len(sys.argv)):
		arg = sys.argv[argi]
		nextArg = sys.argv[argi + 1] if argi + 1 < len(sys.argv) else None

		if arg == '--help' or arg == '-h' or arg == '-H':
			PrintHelp(exitCode = 0)

		elif arg == '--config' or arg == '-c':
			configFile = nextArg

		elif arg == '--interface' or arg == '-i':
			interface = helpers.SanitizeInterfaceName(nextArg)
		
		elif arg == 'stas':
			command = 'stas'
			
		elif arg == 'signals':
			command = 'signals'
			
		elif arg == 'monitor':
			command = 'monitor'

	return configFile, interface, command
	
def GetStas(config, interface = None):
	hadError = False
	stas = []
	
	for hostapdInstanceName in config['hostapd']:
		hostapdInterface = helpers.SanitizeInterfaceName(config['hostapd'][hostapdInstanceName]['interface'])
		
		if not interface is None:
			if interface != hostapdInterface:
				continue
		
		proc = subprocess.run(
			[
				'hostapd_cli',
				'-p',
				'/run/router',
				'-i',
				hostapdInterface,
				'list_sta'
			],
			capture_output = True
		)
		
		if proc.returncode == 0:
			staList = proc.stdout.decode('utf-8').strip().split('\n')
			
			for sta in staList:
				proc = subprocess.run(
					[
						'hostapd_cli',
						'-p',
						'/run/router',
						'-i',
						hostapdInterface,
						'sta',
						sta
					],
					capture_output = True
				)
				
				if proc.returncode == 0:
					staObject = {
						'sta' : sta,
						'interface' : hostapdInterface,
						'timestamp' : time.monotonic()
					}
					
					staInfoList = proc.stdout.decode('utf-8').strip().split('\n')
					
					for info in staInfoList:
						infoFields = info.split('=')
						
						if len(infoFields) == 2:
							staObject[infoFields[0]] = infoFields[1]
								
					stas.append(staObject)
					
				else:
					hadError = True
		else:
			hadError = True
		
	return not hadError, stas
	
def GetSignals(config, interface = None):
	success, stas = GetStas(config, interface)
	hadError = not success
	signals = []
	
	# Ping each STA with hostapd first then collect the signal reading.
	for sta in stas:
		if helpers.IsValidHwAddress(sta['sta']):
			proc = subprocess.run(
				[
					'hostapd_cli',
					'-p',
					'/run/router',
					'-i',
					helpers.SanitizeInterfaceName(sta['interface']),
					'poll_sta',
					sta['sta']
				],
				capture_output = True
			)
			
			if proc.returncode == 0:
				time.sleep(helpers.RandomInRange(0.1, 0.25))
			else:
				# hadError = True
				pass

	if not hadError:
		success, stas = GetStas(config, interface)
		hadError = not success
	
	if not hadError:
		for sta in stas:
			if all(k in sta.keys() for k in ('sta', 'signal', 'interface')):
				staSignalObject = {
					'sta' : sta['sta'],
					'signal' : sta['signal'],
					'interface' : helpers.SanitizeInterfaceName(sta['interface']),
					'timestamp' : time.monotonic()
				}
				signals.append(staSignalObject)
			
	return not hadError, signals
	
def MonitorThread(config, interface):
	global receivedSigQuit
	
	while not receivedSigQuit:
		success, signals = GetSignals(config, interface)
		
		if success:
			print(signals)
			time.sleep(helpers.RandomInRange(0.1, 0.24))
		else:
			break

def WiFiMain():
	configFile, interface, command = ParseArguments()
	monitorThread = None
	
	signal.signal(signal.SIGQUIT, SignalHandler)
	signal.signal(signal.SIGINT, SignalHandler)
	
	if command is None:
		PrintHelp(exitCode = 1)
	
	config = helpers.LoadConfig(configFile, log = False)
	
	if not command is None:
		if command == 'stas':
			_, stas = GetStas(config, interface)
			print(json.dumps(stas))
			
		elif command == 'signals':
			_, signals = GetSignals(config, interface)
			print(json.dumps(signals))
			
		elif command == 'monitor':
			monitorThread = threading.Thread(target = MonitorThread, args = (config, interface))
			monitorThread.start()
			
	if not monitorThread is None:
		monitorThread.join()
		
if __name__ == '__main__':
	sys.exit(WiFiMain())
		
		
