#!/usr/bin/env python

from __future__ import print_function
import locale
import os
import re
import sys 
import subprocess
from dialog import Dialog
from debinterface.interfaces import Interfaces

class Iface:
  def __init__(self, name, description):
    self.name = name
    self.description = description

class Constants:
  DHCP = 'dhcp'
  STATIC = 'static'
  TXT_BACKGROUND_TITLE = 'Network Interface Configuration'
  TXT_ERR_ROOT_REQUIRED = 'root privileges required. run with sudo'
  TXT_NETWORK_CFG_SUCCESS = 'Network configuration completed successfully!\n\n'
  TXT_NETWORK_CFG_ERROR = 'Error occured while configuring network interface!\n\n'
  TXT_WELCOME_TITLE = 'Welcome to pydialog-interfaces configuration!\n\nThis tool helps you to set up your network interface.'
  TXT_SELECT_INTERFACE = 'Select interface'
  TXT_SELECT_SOURCE = 'Select address source'
  TXT_MESSAGE_DHCP = 'Configuring for DHCP provided address...'
  TXT_MESSAGE_STATIC = 'Configuring for static IP address...'
  TXT_MESSAGE_ERROR = '\Zb\Z1Error: %s\n\n\Z0Please try again.'
  TXT_CONFIG_STATIC_TITLE = 'Provie the values for static IP configuration'

def clearquit():
  os.system('clear')
  sys.exit(0)

def run_process(command, stderr=False):
  p = subprocess.Popen([command], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
  output = ""
  while(True):
    retcode = p.poll()
    if stderr:
      line = p.stderr.readline().decode('utf-8')
    else:
      line = p.stdout.readline().decode('utf-8')
    output = output + line

    if retcode is not None:
      break

  return {'retcode': retcode, 'output': output}

def network_restart(selected_iface):
  # check if iface is up
  results = run_process("ifconfig | grep " + selected_iface, stderr=False)
  selected_iface_is_down = True
  for line in results['output'].splitlines():
    if re.match(selected_iface, line):
      selected_iface_is_down = False

    if selected_iface_is_down:
      command = "ifup " + selected_iface
    else:
      command = "ifdown " + selected_iface + " && ifup " + selected_iface

  return run_process(command, stderr=True)

def write_and_display_results(interfaces, selected_iface):
  interfaces.writeInterfaces()
  results = network_restart(selected_iface)
  if results['retcode'] == 0:
    text = Constants.TXT_NETWORK_CFG_SUCCESS
  else:
    text = Constants.TXT_NETWORK_CFG_ERROR

  code = d.msgbox(text + results['output'])
  clearquit()
 
# some sanity checks here, sudo only

locale.setlocale(locale.LC_ALL, '') 
if os.getuid() != 0:
  print(Constants.TXT_ERR_ROOT_REQUIRED)
  sys.exit(1)

# display available interfaces to configure
interfaces = Interfaces()
d = Dialog(dialog='dialog', autowidgetsize=True)
d.set_background_title(Constants.TXT_BACKGROUND_TITLE)

code = d.yesno(Constants.TXT_WELCOME_TITLE, 
                height="15", width=65, yes_label="OK", no_label="Cancel")

if (code == Dialog.CANCEL or code == Dialog.ESC):
  clearquit()

available_adapters = []
available_iface_list = run_process("ifconfig -a | grep eth")['output']

for line in available_iface_list.splitlines():
  elems = line.split(' ', 1)
  iface = Iface(elems[0].strip(), elems[1].strip())
  available_adapters.append(iface)

choices = []
for adapter in available_adapters:
  choices.append((adapter.name, adapter.description))

code, tag = d.menu(Constants.TXT_SELECT_INTERFACE, choices=choices)
if code == Dialog.OK:
  selected_iface = tag
  # check if selected_iface is already listed or not in interfaces file using debinterfaces
  configured_iface = None
  for adapter in interfaces.adapters:
    item = adapter.export()
    if item['name'] == selected_iface:
      configured_iface = item
      break

  # remove from adapter list if it is already configured
  if configured_iface is not None:
    interfaces.removeAdapterByName(selected_iface)

  code, tag = d.menu(Constants.TXT_SELECT_SOURCE, choices=[(Constants.DHCP, 'Dynamic IP'), (Constants.STATIC, 'Static IP')])
  if code == Dialog.OK:
    if tag == Constants.DHCP:
      code = d.infobox(Constants.TXT_MESSAGE_DHCP)

      # simply add
      interfaces.addAdapter({
        'name': selected_iface,
        'auto': True,
        'addrFam': 'inet',
        'source': Constants.DHCP}, 0)

      write_and_display_results(interfaces, selected_iface)

    if tag == Constants.STATIC:
      while True:
        try:
          code, values = d.form(Constants.TXT_CONFIG_STATIC_TITLE, [
                                # title, row_1, column_1, field, row_1, column_20, field_length, input_length
                                ('IP Address', 1, 1, '192.168.0.10', 1, 20, 15, 15),
                                # title, row_2, column_1, field, row_2, column_20, field_length, input_length
                                ('Netmask', 2, 1, '255.255.255.0', 2, 20, 15, 15),
                                # title, row_3, column_1, field, row_3, column_20, field_length, input_length
                                ('Gateway', 3, 1, '192.168.0.1', 3, 20, 15, 15)
                                ], width=70)

          if (code == Dialog.CANCEL or code == Dialog.ESC):
            clearquit()

          code = d.infobox(Constants.TXT_MESSAGE_STATIC)
          # simply add
          interfaces.addAdapter({
            'name': selected_iface,
            'auto': True,
            'addrFam': 'inet',
            'source': Constants.STATIC,
            'address': values[0],
            'netmask': values[1],
            'gateway': values[2]}, 0)

          write_and_display_results(interfaces, selected_iface)
        except Exception, e:
          code = d.msgbox(text=Constants.TXT_MESSAGE_ERROR % e, colors=True)
  else:
    clearquit()
else:
  clearquit()                                                                                                                   

