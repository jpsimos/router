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
import time
import helpers

COMMAND_STA = 1
COMMAND_SIGNALS = 2

Frequencies = {
	'2.4' : [
		{ 'channel' : 1, 'frequency' : 2412 },
		{ 'channel' : 2, 'frequency' : 2417 },
		{ 'channel' : 3, 'frequency' : 2422 },
		{ 'channel' : 4, 'frequency' : 2427 },
		{ 'channel' : 5, 'frequency' : 2432 },
		{ 'channel' : 6, 'frequency' : 2437 },
		{ 'channel' : 7, 'frequency' : 2442 },
		{ 'channel' : 8, 'frequency' : 2447 },
		{ 'channel' : 9, 'frequency' : 2452 },
		{ 'channel' : 10, 'frequency' : 2457 },
		{ 'channel' : 11, 'frequency' : 2462 },
		{ 'channel' : 12, 'frequency' : 2467 },
		{ 'channel' : 13, 'frequency' : 2472 },
		{ 'channel' : 14, 'frequency' : 2484 }
	],
	'5' : [
		{ 'channel' : 36, 'frequency' : 5180 },
		{ 'channel' : 40, 'frequency' : 5200 },
		{ 'channel' : 44, 'frequency' : 5220 },
		{ 'channel' : 48, 'frequency' : 5240 },
		{ 'channel' : 52, 'frequency' : 5260 },
		{ 'channel' : 56, 'frequency' : 5280 },
		{ 'channel' : 60, 'frequency' : 5300 },
		{ 'channel' : 64, 'frequency' : 5320 },
		{ 'channel' : 68, 'frequency' : 5340 },
		{ 'channel' : 72, 'frequency' : 5360 },
		{ 'channel' : 76, 'frequency' : 5380 },
		{ 'channel' : 80, 'frequency' : 5400 },
		{ 'channel' : 84, 'frequency' : 5420 },
		{ 'channel' : 88, 'frequency' : 5440 },
		{ 'channel' : 92, 'frequency' : 5460 },
		{ 'channel' : 96, 'frequency' : 5480 },
		{ 'channel' : 100, 'frequency' : 5500 },
		{ 'channel' : 104, 'frequency' : 5520 },
		{ 'channel' : 108, 'frequency' : 5540 },
		{ 'channel' : 112, 'frequency' : 5560 },
		{ 'channel' : 116, 'frequency' : 5580 },
		{ 'channel' : 120, 'frequency' : 5600 },
		{ 'channel' : 124, 'frequency' : 5620 },
		{ 'channel' : 128, 'frequency' : 5640 },
		{ 'channel' : 132, 'frequency' : 5660 },
		{ 'channel' : 136, 'frequency' : 5680 },
		{ 'channel' : 140, 'frequency' : 5700 },
		{ 'channel' : 144, 'frequency' : 5720 },
		{ 'channel' : 149, 'frequency' : 5745 },
		{ 'channel' : 153, 'frequency' : 5765 },
		{ 'channel' : 157, 'frequency' : 5785 },
		{ 'channel' : 161, 'frequency' : 5805 },
		{ 'channel' : 165, 'frequency' : 5825 },
		{ 'channel' : 169, 'frequency' : 5845 },
		{ 'channel' : 173, 'frequency' : 5865 },
		{ 'channel' : 177, 'frequency' : 5885 }
	]
}

def PrintHelp(exitCode = None):
	print('linux router wifi')
	print(f'{sys.argv[0]} [options] [command] args...')
	print()
	print(' --help           -h          Show this help message.')
	print(' --config         -c          Use provided config file.')
	print()
	print('Commands')
	print(' stas             Show STAs.')
	print(' signal           Show STA signals.')
	print('Author Jacob A. Psimos')
	
	if exitCode is not None:
		sys.exit(exitCode)

def ParseArguments():
	command = None
	configFile = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'config.json')
	
	if len(sys.argv) == 1:
		PrintHelp(exitCode = 1)
	
	for argi in range(1, len(sys.argv)):
		arg = sys.argv[argi]
		nextArg = sys.argv[argi + 1] if argi + 1 < len(sys.argv) else None

		if arg == '--help' or arg == '-h':
			PrintHelp(exitCode = 0)

		elif arg == '--config' or arg == '-c':
			configFile = nextArg
			
		elif arg == 'stas' : 
			command = COMMAND_STA
			
		elif arg == 'signals':
			command = COMMAND_SIGNALS

	return configFile, command
	
def GetStas(config):
	hadError = False
	stas = []
	
	for hostapdInstanceName in config['hostapd']:
		hostapdInterface = helpers.SanitizeInterfaceName(config['hostapd'][hostapdInstanceName]['interface'])
		
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
					staObject = { 'sta' : sta, 'interface' : hostapdInterface }
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
	
def GetSignals(config):
	success, stas = GetStas(config)
	hadError = not success
	signals = []
	
	for sta in stas:
		signals.append({ 'sta' : sta['sta'], 'signal' : sta['signal'] })
			
	return not hadError, signals

def WiFiMain():
	configFile, command = ParseArguments()
	
	if command is None:
		PrintHelp(exitCode = 1)
	
	config = helpers.LoadConfig(configFile)
	
	if not command is None:
		if command == COMMAND_STA:
			_, stas = GetStas(config)
			print(json.dumps(stas))
			
		elif command == COMMAND_SIGNALS:
			_, signals = GetSignals(config)
			print(json.dumps(signals))
			
if __name__ == '__main__':
	sys.exit(WiFiMain())
		
		