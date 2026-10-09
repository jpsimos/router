#!/usr/bin/env python3

'''
	Author Jacob A. Psimos
	
	0. Interprets 'config.json' file (or one passed in via arguments.)
	1. Sets up bridge interfaces and associates interfaces with it.
	2. Generates dnsmasq config files and runs the daemon.
	3. Generates hostapd config files and runs the daemon.
	4. Tears down the bridges, dnsmasq daemon(s), and hostapd daemon(s).
'''

import os
import sys
import json
import syslog
import subprocess
import traceback
import helpers

class Router:
	m_noBridges = False
	m_noDnsmasq = False
	m_noHostapd = False
	m_config = None
	
	def __init__(self, configFilePath = None, noBridges = False, noDnsmasq = False, noHostapd = False):
		self.m_config = helpers.LoadConfig(configFilePath)
		self.m_noBridges = noBridges
		self.m_noDnsmasq = noDnsmasq
		self.m_noHostapd = noHostapd
			
	def Reset(self):
		self.TeardownBridges(stopOnError = False)
		self.TeardownDnsmasq(stopOnError = False)
		self.TeardownHostapd(stopOnError = False)
		
	def Start(self):
		hadErrorSettingupBridges = False
		hadErrorSettingupFirewall = False
		hadErrorSettingupDnsmasq = False
		hadErrorSettingupHostapd = False
		
		if not self.m_noBridges:
			hadErrorSettingupBridges = not self.SetupBridges()
			
		hadErrorSettingupFirewall = self.SetupFirewall()
			
		if not self.m_noDnsmasq and not hadErrorSettingupBridges:
			hadErrorSettingupDnsmasq = not self.SetupDnsmasq()
			
		if not self.m_noHostapd and not hadErrorSettingupBridges and not hadErrorSettingupDnsmasq:
			hadErrorSettingupHostapd =  not self.SetupHostapd()
			
		return not hadErrorSettingupBridges and not hadErrorSettingupDnsmasq and not hadErrorSettingupHostapd
		
	def Stop(self):
		hadErrorTearingdownDnsmasq = False
		hadErrorTearingdownHostapd = False
		hadErrorTearingdownBridges = False
		
		if not self.m_noDnsmasq:
			hadErrorTearingdownDnsmasq = not self.TeardownDnsmasq()
			
		if not self.m_noHostapd:
			hadErrorTearingdownHostapd = not self.TeardownHostapd()
			
		if not self.m_noBridges:
			hadErrorTearingdownBridges = not self.TeardownBridges()
	
		return not hadErrorTearingdownBridges and not hadErrorTearingdownDnsmasq and not hadErrorTearingdownHostapd
		
	def Restart(self):
		return self.Reset() and self.Start()
		
	def Reload(self):
		hadError = False
		
		for dnsmasqInstanceName in self.m_config['dnsmasq']:
			dnsmasqConfFilePath = os.path.join('/run/router', helpers.SanitizeFileName(f'dnsmasq-{dnsmasqInstanceName}.conf'))
			dnsmasqPidFilePath = os.path.join('/run/router', helpers.SanitizeFileName(f'dnsmasq-{dnsmasqInstanceName}.pid'))
			
			if os.path.isfile(dnsmasqPidFilePath):
				with open(dnsmasqPidFilePath, 'r') as dnsmasqPidFile:
					dnsmasqPid = dnsmasqPidFile.read().strip()
					
					if dnsmasqPid.isnumeric():
						proc = subprocess.run([
							'kill',
							'-HUP',
							dnsmasqPid
						])
						
						if proc.returncode != 0:
							hadError = True
			
		for hostapdInstanceName in self.m_config['hostapd']:
			hostapdConfFilePath = os.path.join('/run/router', helpers.SanitizeFileName(f'hostapd-{hostapdInstanceName}.conf'))
			hostapdPidFilePath = os.path.join('/run/router', helpers.SanitizeFileName(f'hostapd-{hostapdInstanceName}.pid'))
			
			if os.path.isfile(hostapdConfFilePath):
				with open(hostapdConfFilePath, 'r') as hostapdPidFile:
					hostapdPid = hostapdPidFile.read().strip()
					
					if hostapdPid.isnumeric():
						proc = subprocess.run([
							'kill',
							'-HUP',
							hostapdPid
						])
						
						if proc.returncode != 0:
							hadError = True
							
		return not hadError
		
	def SetupFirewall(self):
		hadError = False
		
		proc = subprocess.run([
			'iptables-restore',
			'/opt/router/firewall.ipt'
		])
		
		if proc.returncode != 0:
			hadError = True
			raise Exception(f'{__file__}:{sys._getframe().f_lineno} Setting up firewall with iptables-restore failed with returncode={proc.returncode}. Permissions?')
			
		return not hadError

	def SetupBridges(self):
		hadError = False
		
		for interfaceName in self.m_config['interfaces'].keys():
			if self.m_config['interfaces'][interfaceName]['type'] == 'bridge':
			
				# TODO: validate legitness of bridgeBroadcastAddress with subnet
				bridgeInterfaceName = helpers.SanitizeInterfaceName(interfaceName)
				bridgeHwAddress = self.m_config['interfaces'][interfaceName]['hwaddr']
				bridgeIpAddress = self.m_config['interfaces'][interfaceName]['address']
				bridgeSubnet = self.m_config['interfaces'][interfaceName]['subnet']
				bridgeBroadcastAddress = self.m_config['interfaces'][interfaceName]['broadcast']
				bridgeMetric = self.m_config['interfaces'][interfaceName]['metric']
				bridgeStp = '1' if self.m_config['interfaces'][interfaceName]['stp'] is True else '0'
				
				if 'enable' in self.m_config['interfaces'][interfaceName].keys():
					if self.m_config['interfaces'][interfaceName]['enable'] is False:
						continue
						
				if helpers.InterfaceExists(bridgeInterfaceName):
					# Try to remove the existing interface.
					if not helpers.DeleteInterface(bridgeInterfaceName):
						hadError = True
						raise Exception(f'{__file__}:{sys._getframe().f_lineno} Bridge interface {bridgeInterfaceName} is already configured. Remove it externally first and retry.')
				
				if not helpers.IsValidHwAddress(bridgeHwAddress):
					hadError = True
					raise Exception(f'{__file__}:{sys._getframe().f_lineno} Invalid HW Address for bridge instance {bridgeInstanceName}.')
			
				if not helpers.IsValidIpAddress(bridgeIpAddress):
					hadError = True
					raise Exception(f'{__file__}:{sys._getframe().f_lineno} Invalid HW Address for bridge interface {bridgeInterfaceName}.')
					
				if not helpers.IsValidIpAddress(bridgeBroadcastAddress):
					hadError = True
					raise Exception(f'{__file__}:{sys._getframe().f_lineno} Invalid broadcast address for bridge interface {bridgeInterfaceName}.')
					
				if not bridgeSubnet.isnumeric():
					hadError = True
					raise Exception(f'{__file__}:{sys._getframe().f_lineno} Invalid subnet for bridge interface {bridgeInterfaceName}.')
					
				if not bridgeMetric.isnumeric():
					hadError = True
					raise Exception(f'{__file__}:{sys._getframe().f_lineno} Invalid metric for bridge interface {bridgeInterfaceName}.')
				
				proc = subprocess.run([
					'ip',
					'link',
					'add',
					'name',
					bridgeInterfaceName,
					'address',
					bridgeHwAddress,
					'type',
					'bridge'
				])
				
				if proc.returncode != 0:
					hadError = True
					raise Exception(f'{__file__}:{sys._getframe().f_lineno} Adding bridge {bridgeInterfaceName} failed with returncode={proc.returncode}. Permissions?')
				
				proc = subprocess.run([
					'ip',
					'link',
					'set',
					bridgeInterfaceName,
					'down'
				])
				
				if proc.returncode != 0:
					hadError = True
					raise Exception(f'{__file__}:{sys._getframe().f_lineno} Setting bridge {bridgeInterfaceName} down failed with returncode={proc.returncode}. Permissions?')
					
				# Add bridge slaves
				# Skip non lan interface types. Let hostapd handle WiFi interfaces.
				for configInterfaceName in self.m_config['interfaces'][interfaceName]['interfaces']:
				
					if self.m_config['interfaces'][configInterfaceName]['type'] != 'lan':
						continue
						
					# TODO: check hwaddress for expectedness
					if helpers.InterfaceExists(configInterfaceName):
						proc = subprocess.run([
							'ip',
							'link',
							'set',
							configInterfaceName,
							'down'
						])
					
						if proc.returncode != 0:
							hadError = True
							raise Exception(f'{__file__}:{sys._getframe().f_lineno} Setting slave interface {configInterfaceName} down failed with returncode={proc.returncode}. Permissions?')
							
						proc = subprocess.run([
							'ip',
							'link',
							'set',
							configInterfaceName,
							'master',
							bridgeInterfaceName
						])
					
						if proc.returncode != 0:
							hadError = True
							raise Exception(f'{__file__}:{sys._getframe().f_lineno} Adding slave interface {configInterfaceName} to {bridgeInterfaceName} failed with returncode={proc.returncode}. Permissions?')

						proc = subprocess.run([
							'ip',
							'link',
							'set',
							configInterfaceName,
							'up'
						])
					
						if proc.returncode != 0:
							hadError = True
							raise Exception(f'{__file__}:{sys._getframe().f_lineno} Setting slave interface {configInterfaceName} up failed with returncode={proc.returncode}. Permissions?')
							
						proc = subprocess.run([
							'ip',
							'link',
							'set',
							configInterfaceName,
							'promisc',
							'on'
						])
					
						if proc.returncode != 0:
							hadError = True
							raise Exception(f'{__file__}:{sys._getframe().f_lineno} Setting slave interface {configInterfaceName} promisc on failed with returncode={proc.returncode}. Permissions?')
				
				# Set bridge master STP and IP address
				proc = subprocess.run([
					'ip',
					'link',
					'set',
					bridgeInterfaceName,
					'up'
				])
				
				if proc.returncode != 0:
					hadError = True
					raise Exception(f'{__file__}:{sys._getframe().f_lineno} Setting bridge {bridgeInterfaceName} up failed with returncode={proc.returncode}. Permissions?')
					
				proc = subprocess.run([
					'ip',
					'link',
					'set',
					bridgeInterfaceName,
					'type',
					'bridge',
					'stp_state',
					bridgeStp
				])
				
				if proc.returncode != 0:
					hadError = True
					raise Exception(f'{__file__}:{sys._getframe().f_lineno} Setting bridge {bridgeInterfaceName} STP failed with returncode={proc.returncode}. Permissions?')
					
				proc = subprocess.run([
					'ip',
					'address',
					'add',
					f'{bridgeIpAddress}/{bridgeSubnet}',
					'broadcast',
					bridgeBroadcastAddress,
					'metric',
					bridgeMetric,
					'dev',
					bridgeInterfaceName
				])
				
				if proc.returncode != 0:
					hadError = True
					raise Exception(f'{__file__}:{sys._getframe().f_lineno} Setting bridge {bridgeInterfaceName} ip address failed with returncode={proc.returncode}. Permissions?')
					
				# Enable ipv4 forwarding.
				proc = subprocess.run([
					'sysctl',
					'-q',
					'-w',
					'net.ipv4.ip_forward=1'
				])
				
				if proc.returncode != 0:
					hadError = True
					raise Exception(f'{__file__}:{sys._getframe().f_lineno} Setting net.ipv4.ip_forward=1 failed with returncode={proc.returncode}. Permissions?')
	
		return not hadError
							
	def TeardownBridges(self, stopOnError = False):
		hadError = False
		
		# Disable ipv4 forwarding.
		proc = subprocess.run([
			'sysctl',
			'-q',
			'-w',
			'net.ipv4.ip_forward=0'
		])
	
		if proc.returncode != 0:
			hadError = True
			raise Exception(f'{__file__}:{sys._getframe().f_lineno} Setting net.ipv4.ip_forward=0 failed with returncode={proc.returncode}. Permissions?')
			
		for interfaceName in self.m_config['interfaces'].keys():
			if self.m_config['interfaces'][interfaceName]['type'] == 'bridge':
				bridgeInterfaceName = helpers.SanitizeInterfaceName(interfaceName)
				bridgeHwAddress = self.m_config['interfaces'][interfaceName]['hwaddr']
				bridgeIpAddress = self.m_config['interfaces'][interfaceName]['address']
				bridgeSubnet = self.m_config['interfaces'][interfaceName]['subnet']
				bridgeBroadcastAddress = self.m_config['interfaces'][interfaceName]['broadcast']
				bridgeMetric = self.m_config['interfaces'][interfaceName]['metric']
				bridgeStp = '1' if self.m_config['interfaces'][interfaceName]['stp'] is True else '0'
				
				if 'enable' in self.m_config['interfaces'][interfaceName].keys():
					if self.m_config['interfaces'][interfaceName]['enable'] is False:
						continue
						
				if helpers.InterfaceExists(bridgeInterfaceName, bridgeHwAddress):
				
					# Remove slave interfaces.
					for configInterfaceName in self.m_config['interfaces'][interfaceName]['interfaces']:
						if self.m_config['interfaces'][configInterfaceName]['type'] != 'lan':
							continue
							
						if helpers.InterfaceExists(configInterfaceName):
							proc = subprocess.run([
								'ip',
								'link',
								'set',
								configInterfaceName,
								'down'
							])
					
						if proc.returncode != 0:
							hadError = True
							if stopOnError:
								raise Exception(f'{__file__}:{sys._getframe().f_lineno} Setting bridge slave {configInterfaceName} down failed with returncode={proc.returncode}. Permissions?')

						proc = subprocess.run([
							'ip',
							'link',
							'set',
							configInterfaceName,
							'nomaster'
						])
						
						if proc.returncode != 0:
							hadError = True
							if stopOnError:
								raise Exception(f'{__file__}:{sys._getframe().f_lineno} Removing bridge master {configInterfaceName} failed with returncode={proc.returncode} Permissions?')
							
						proc = subprocess.run([
							'ip',
							'link',
							'set',
							configInterfaceName,
							'promisc',
							'off'
						])
						
						if proc.returncode != 0:
							hadError = True
							if stopOnError:
								raise Exception(f'{__file__}:{sys._getframe().f_lineno} Setting slave interface {configInterfaceName} promisc off failed with returncode={proc.returncode}. Permissions?')
						
					# Remove the bridge master interface.
					proc = subprocess.run([
						'ip',
						'address',
						'flush',
						'dev',
						bridgeInterfaceName
					])
						
					if proc.returncode != 0:
						hadError = True
						if stopOnError:
							raise Exception(f'{__file__}:{sys._getframe().f_lineno} Flush bridge address {bridgeInterfaceName} failed with returncode={proc.returncode} Permissions?')
						
					proc = subprocess.run([
						'ip',
						'link',
						'del',
						bridgeInterfaceName
					])
						
					if proc.returncode != 0:
						hadError = True
						if stopOnError:
							raise Exception(f'{__file__}:{sys._getframe().f_lineno} Deleting bridge {bridgeInterfaceName} failed with returncode={proc.returncode} Permissions?')
					
		return not hadError
			
	def SetupDnsmasq(self):
		hadError = False
		
		for dnsmasqInstanceName in self.m_config['dnsmasq']:
			dnsmasqConf = []
			dnsmasqInterface = helpers.SanitizeInterfaceName(self.m_config['dnsmasq'][dnsmasqInstanceName]['interface'])
			dnsmasqAddress = self.m_config['dnsmasq'][dnsmasqInstanceName]['address']
			dnsmasqDhcpBegin = self.m_config['dnsmasq'][dnsmasqInstanceName]['dhcp-begin']
			dnsmasqDhcpEnd = self.m_config['dnsmasq'][dnsmasqInstanceName]['dhcp-end']
			dnsmasqLease = self.m_config['dnsmasq'][dnsmasqInstanceName]['lease']
			dnsmasqConfFilePath = os.path.join('/run/router', helpers.SanitizeFileName(f'dnsmasq-{dnsmasqInstanceName}.conf'))
			dnsmasqPidFilePath = os.path.join('/run/router', helpers.SanitizeFileName(f'dnsmasq-{dnsmasqInstanceName}.pid'))
			hostName = helpers.GetHostName()
			dnsmasqConfContents = ''
			
			if not helpers.IsValidIpAddress(dnsmasqAddress) or not helpers.IsValidIpAddress(dnsmasqDhcpBegin) or not helpers.IsValidIpAddress(dnsmasqDhcpEnd):
				hadError = True
				raise Exception(f'{__file__}:{sys._getframe().f_lineno} Invalid IP Address(es) for dnsmasq instance {dnsmasqInstanceName}.')
			
			if 'enable' in self.m_config['dnsmasq'][dnsmasqInstanceName].keys():
				if self.m_config['dnsmasq'][dnsmasqInstanceName]['enable'] is False:
					continue
			
			if 'interface' in self.m_config['dnsmasq'][dnsmasqInstanceName].keys():
				if helpers.InterfaceExists(self.m_config['dnsmasq'][dnsmasqInstanceName]['interface']):
					dnsmasqConf.append(('interface', helpers.SanitizeInterfaceName(self.m_config['dnsmasq'][dnsmasqInstanceName]['interface'])))
				else:
					hadError = True
					raise Exception(f'{__file__}:{sys._getframe().f_lineno} Interface does not exist.')
					
			dnsmasqConf.append(('dhcp-option', f'option:router,{dnsmasqAddress}'))
			dnsmasqConf.append(('dhcp-range', f'{dnsmasqDhcpBegin},{dnsmasqDhcpEnd},{dnsmasqLease}'))
			dnsmasqConf.append(('dhcp-option', f'option:dns-server,{dnsmasqAddress}'))
			dnsmasqConf.append(('listen-address', dnsmasqAddress))
			
			if 'domain' in self.m_config['dnsmasq'][dnsmasqInstanceName].keys():
				domain = self.m_config['dnsmasq'][dnsmasqInstanceName]['domain']
				dnsmasqConf.append(('domain', domain))
				dnsmasqConf.append(('local', '/' + domain + '/'))
				dnsmasqConf.append(('dhcp-option', 'option:domain-search,' + domain))
				dnsmasqConf.append(('host-record', f'{hostName},{hostName}.{domain},{dnsmasqAddress}'))
				dnsmasqConf.append(('expand-hosts', ''))
				dnsmasqConf.append(('domain-needed', ''))

			for dnsmasqConfOption, dnsmasqConfValue in dnsmasqConf:
				if len(dnsmasqConfValue) > 0:
					dnsmasqConfContents += f"{dnsmasqConfOption}={dnsmasqConfValue}\n"
				else:
					dnsmasqConfContents += f"{dnsmasqConfOption}\n"
					
			if 'append' in self.m_config['dnsmasq'][dnsmasqInstanceName].keys():
				sanitizedAppendFilePath = helpers.SanitizeFileName(self.m_config['dnsmasq'][dnsmasqInstanceName]['append'], allowSlashes = True)
				
				with open(sanitizedAppendFilePath, 'r', encoding = 'utf-8') as dnsmasqAppendFile:
					dnsmasqConfContents += dnsmasqAppendFile.read()
			
			with open(dnsmasqConfFilePath, 'w', encoding = 'utf-8') as dnsmasqConfFile:
				dnsmasqConfFile.write(dnsmasqConfContents)
				
			proc = subprocess.run([
				'dnsmasq',
				'-g',
				'router',
				'--test',
				'-C',
				dnsmasqConfFilePath
			])
			
			if proc.returncode != 0:
				hadError = True
				raise Exception(f'{__file__}:{sys._getframe().f_lineno} dnsmasq conf is invalid.')
				
			proc = subprocess.run([
				'dnsmasq',
				'-g',
				'router',
				'-x',
				dnsmasqPidFilePath,
				'-C',
				dnsmasqConfFilePath
			])
			
			if proc.returncode != 0:
				hadError = True
				raise Exception(f'{__file__}:{sys._getframe().f_lineno} dnsmasq exited with returncode={proc.returncode} Permissions?')	

		return not hadError
		
	def SetupHostapd(self):
		hadError = False
		ranRfkillUnblock = False
		
		for hostapdInstanceName in self.m_config['hostapd']:
			hostapdInterface = self.m_config['hostapd'][hostapdInstanceName]['interface']
			hostapdBridge = self.m_config['hostapd'][hostapdInstanceName]['bridge']
			hostapdConfFilePath = os.path.join('/run/router', helpers.SanitizeFileName(f'hostapd-{hostapdInstanceName}.conf'))
			hostapdPidFilePath = os.path.join('/run/router', helpers.SanitizeFileName(f'hostapd-{hostapdInstanceName}.pid'))
			hostapdConfContents = ''
			hostapdConf = []
			
			if 'enable' in self.m_config['hostapd'][hostapdInstanceName].keys():
				if self.m_config['hostapd'][hostapdInstanceName]['enable'] is False:
					continue
			
			if 'interface' in self.m_config['hostapd'][hostapdInstanceName].keys():
				if helpers.InterfaceExists(self.m_config['hostapd'][hostapdInstanceName]['interface']):
					hostapdConf.append(('interface', helpers.SanitizeInterfaceName(self.m_config['hostapd'][hostapdInstanceName]['interface'])))
				else:
					hadError = True
					raise Exception(f'{__file__}:{sys._getframe().f_lineno} Hostapd interface does not exist.')
					
			if 'bridge' in self.m_config['hostapd'][hostapdInstanceName].keys():
				if helpers.InterfaceExists(self.m_config['hostapd'][hostapdInstanceName]['bridge']):
					hostapdConf.append(('bridge', helpers.SanitizeInterfaceName(self.m_config['hostapd'][hostapdInstanceName]['bridge'])))
				else:
					hadError = True
					raise Exception(f'{__file__}:{sys._getframe().f_lineno} Hostapd bridge interface does not exist.')
			
			for hostapdConfOption, hostapdConfValue in hostapdConf:
				if len(hostapdConfValue) > 0:
					hostapdConfContents += f"{hostapdConfOption}={hostapdConfValue}\n"
				else:
					hostapdConfContents += f"{hostapdConfOption}\n"
					
			if 'append' in self.m_config['hostapd'][hostapdInstanceName].keys():
				sanitizedAppendFilePath = helpers.SanitizeFileName(self.m_config['hostapd'][hostapdInstanceName]['append'], allowSlashes = True)
				
				with open(sanitizedAppendFilePath, 'r', encoding = 'utf-8') as hostapdAppendFile:
					hostapdConfContents += hostapdAppendFile.read()
				
			with open(hostapdConfFilePath, 'w', encoding = "utf-8") as hostapdConfFile:
				hostapdConfFile.write(hostapdConfContents)
			
			# Before running hostapd for the first time, run rfkill to unblock the PHYs.
			if not ranRfkillUnblock:
				if helpers.RunRfkill(unblockAll = True):
					ranRfkillUnblock = True
				else:
					hadError = True
					raise Exception(f'{__file__}:{sys._getframe().f_lineno} rfkill failed.')
			
			proc = subprocess.run([
				'hostapd',
				'-dd',
				'-K',
				'-t',
				'-B',
				'-P',
				hostapdPidFilePath,
				hostapdConfFilePath
			])
			
			if proc.returncode != 0:
				hadError = True
				raise Exception(f'{__file__}:{sys._getframe().f_lineno} hostapd exited with returncode={proc.returncode} Permissions?')	

		return not hadError
		
	def TeardownDnsmasq(self, stopOnError = False):
		hadError = False

		for dnsmasqInstanceName in self.m_config['dnsmasq']:
			dnsmasqConfFilePath = os.path.join('/run/router', helpers.SanitizeFileName(f'dnsmasq-{dnsmasqInstanceName}.conf'))
			dnsmasqPidFilePath = os.path.join('/run/router', helpers.SanitizeFileName(f'dnsmasq-{dnsmasqInstanceName}.pid'))
			
			if os.path.isfile(dnsmasqPidFilePath):
				with open(dnsmasqPidFilePath, 'r') as dnsmasqPidFile:
					dnsmasqPid = ''.join(c for c in dnsmasqPidFile.read() if c.isdigit())
	
					proc = subprocess.run([
						'kill',
						dnsmasqPid
					])
					
					if proc.returncode != 0:
						hadError = True
						if stopOnError:
							raise Exception('{__file__}:{sys._getframe().f_lineno} Kill dnsmasq (pid={dnsmasqPid}) exited with returncode={proc.returncode} Permissions?')
					
			if os.path.isfile(dnsmasqPidFilePath):
				os.unlink(dnsmasqPidFilePath)
				
			if os.path.isfile(dnsmasqConfFilePath):
				os.unlink(dnsmasqConfFilePath)
				
		return not hadError
		
	def TeardownHostapd(self, stopOnError = False):
		hadError = False

		for hostapdInstanceName in self.m_config['hostapd']:
			hostapdConfFilePath = os.path.join('/run/router', helpers.SanitizeFileName(f'hostapd-{hostapdInstanceName}.conf'))
			hostapdPidFilePath = os.path.join('/run/router', helpers.SanitizeFileName(f'hostapd-{hostapdInstanceName}.pid'))
			
			if os.path.isfile(hostapdPidFilePath):
				with open(hostapdPidFilePath, 'r') as hostapdPidFile:
					hostapdPid = hostapdPidFile.read().strip()
					
					if hostapdPid.isnumeric():	
						proc = subprocess.run([
							'kill',
							hostapdPid
						])
						
						if proc.returncode != 0:
							hadError = True
							if stopOnError:
								raise Exception(f'{__file__}:{sys._getframe().f_lineno} Kill hostapd (pid={hostapdPid}) exited with returncode={proc.returncode} Permissions?')

			if os.path.isfile(hostapdPidFilePath):
				os.unlink(hostapdPidFilePath)
				
			if os.path.isfile(hostapdConfFilePath):
				os.unlink(hostapdConfFilePath)
				
			if not helpers.RunRfkill(unblockAll = False):
				hadError = True
				if stopOnError:
					raise Exception(f'{__file__}:{sys._getframe().f_lineno} rfkill failed.')
				
		return not hadError

