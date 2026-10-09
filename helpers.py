#!/usr/bin/env python3

'''
	Author Jacob A. Psimos
	
	Helper procedures.
	
	TODO: deprecated rfkill command
'''

import sys
import os
import syslog
import json
import traceback
import time
import subprocess
import re

def LoadConfig(configFilePath):
	hadError = False
	haveWanInterface = False
	config = None
	
	with open(configFilePath, 'r') as configFile:
		config = json.loads(configFile.read())

	# Verify the provided interfaces in the config. Should be only one WAN interface.
	if 'interfaces' in config.keys():
		for configInterfaceName in config['interfaces']:
			if InterfaceExists(configInterfaceName, config['interfaces'][configInterfaceName]['hwaddr']):
				if config['interfaces'][configInterfaceName]['type'].lower() == 'wan':
					if not haveWanInterface:
						haveWanInterface = True
					else:
						hadError = True
						raise Exception(f'{__file__}:{sys._getframe().f_lineno} Interface {configInterfaceName} conflicts for type "wan."')
			else:
				syslog.syslog(syslog.LOG_ERR, f'{__file__}:{sys._getframe().f_lineno} Interface {configInterfaceName} does not exist or does not match the expected hwaddr.')
	
	if hadError is True:
		config = None
		
	return config

def GetHostName():
	hostName = None
	with open('/etc/hostname', 'r') as hostNameFile:
		hostName = hostNameFile.read().strip()
	return hostName
	
def SanitizeFileName(fileName, allowSlashes = False):
	sanitizedFilename = ''.join(c for c in fileName if c.isdigit() or c.isalnum() or c == ' ' or c == '.' or c == '-' or c == '_' or (True if allowSlashes is True and c == '/' else False))
	return sanitizedFilename.replace('..', '')
	
def SanitizeInterfaceName(interfaceName):
	sanitizedInterfaceName = ''.join(c for c in interfaceName if c.isdigit() or c.isalnum() or c == '.' or c == '-' or c == '_')
	return sanitizedInterfaceName.replace('..', '')
	
def IsValidIpAddress(ipAddress):
	isValid = False
	parts = ipAddress.split('.')
	
	if len(parts) == 4:
		for part in parts:
			if len(part) > 0 and len(part) < 4:
				isValid = True
				
				for c in part:
					if not c.isdigit():
						isValid = False
						break
						
			if not isValid:
				break
	
	return isValid
	
def IsValidHwAddress(hwAddress):
	isValid = False
	parts = hwAddress.split(':')
	
	if len(parts) == 6:
		isValid = True
		
		for part in parts:
			if len(part) != 2:
				isValid = False
				break
				
			for hexChar in part.lower():
				if not ((ord(hexChar) >= 97 and ord(hexChar) <= 102) or (ord(hexChar) >= 48 and ord(hexChar) <= 57)):
					isValid = False
					break
					
	return isValid
	
def InterfaceExists(interfaceName, expectedHwAddr = None):
	sysfsPath = os.path.join('/sys/class/net', SanitizeInterfaceName(interfaceName))
	sysfsAddressFilePath = os.path.join(sysfsPath, 'address')
	doesHwAddrMatch = True if expectedHwAddr is None else False
	exists = os.path.islink(sysfsPath)
	
	if exists:
		with open(sysfsAddressFilePath, 'r') as sysfsAddressFile:
			sysfsAddress = sysfsAddressFile.read().strip()
			if IsValidHwAddress(sysfsAddress):
				if expectedHwAddr is not None and IsValidHwAddress(expectedHwAddr):
					doesHwAddrMatch = True if expectedHwAddr.lower() == sysfsAddress.lower() else False

	return exists and doesHwAddrMatch
	
def GetInterfaceHwAddress(interfaceName):
	sysfsPath = os.path.join('/sys/class/net', SanitizeInterfaceName(interfaceName))
	sysfsAddressFilePath = os.path.join(sysfsPath, 'address')
	returnHwAddress = None
	
	if os.path.islink(sysfsPath):
		with open(sysfsAddressFilePath, 'r') as sysfsAddressFile:
			sysfsAddress = sysfsAddressFile.read().strip()
			if IsValidHwAddress(sysfsAddress):
				returnHwAddress = sysfsAddress.lower()
				
	return returnHwAddress
	
def RemoveInterfaceAltnames(interfaceName):
	hadError = False
	sanitizedInterfaceName = SanitizeInterfaceName(interfaceName)

	proc = subprocess.run(
		[
			'ip',
			'link',
			'show',
			sanitizedInterfaceName
		],
		capture_output = True
	)
	
	if proc.returncode == 0:
		altnames = re.findall(r"(?m)^\s*altname\s+(\S+)", proc.stdout.decode('utf-8'))
		
		for altname in altnames:
			sanitizedAltname = SanitizeInterfaceName(altname)
			
			proc = subprocess.run([
				'ip',
				'link',
				'property',
				'del',
				sanitizedInterfaceName,
				'altname',
				sanitizedAltname
			])
			
			if proc.returncode != 0:
				hadError = True
			
	return not hadError
	
def RunRfkill(unblockAll = True):
	hadError = False
	
	proc = subprocess.run(
		[
			'rfkill',
			'unblock' if unblockAll is True else 'block',
			'all'
		]
	)
	
	if proc.returncode != 0:
		hadError = True
		
	return not hadError
	
def DeleteInterface(interfaceName):
	hadError = False
	sanitizedInterfaceName = SanitizeInterfaceName(interfaceName)
	
	proc = subprocess.run(
		[
			'ip',
			'link',
			'del',
			sanitizedInterfaceName
		]
	)
	
	if proc.returncode != 0:
		hadError = True
		
	return not hadError