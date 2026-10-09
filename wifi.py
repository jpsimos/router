#!/usr/bin/env python3

'''
	Author Jacob A. Psimos
	
	Manager class to scan phys and configure hostapd instances.
'''

import os
import sys
import json
import subprocess
import time

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

class WiFi:
	m_routerInstance = None

	def __init__(self, routerInstance):
		
	def HostapdCommand(self, interface, command):
		pass
		
		