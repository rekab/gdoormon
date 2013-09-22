# v1.0 by Chris Jones <cmsj@tenshu.net>
# Copyright (C) 2011 Chris Jones
# This script is released under the GNU GPL v2 license.
# From http://bazaar.launchpad.net/~cmsj/+junk/munin-plugins/view/head:/snmp__airport

import netsnmp
import logging


def GetNumClients(host):
  """Get the number of wireless clients connected to an Airport.

  Args:
    host: hostname
  Returns:
    integer
  """
  wirelessNumberOID = '.1.3.6.1.4.1.63.501.3.2.1.0'

  logging.log(logging.DEBUG, "polling SNMP for client number")
  retval = int(netsnmp.snmpget(netsnmp.Varbind(wirelessNumberOID), 
      Version=2, DestHost=host, 
      Community='public')[0])

  logging.log(logging.DEBUG, "found %d clients" % retval)
  return retval


def TableToDict(table, num):
  """Get a dictionary of SNMP data.
  
  The netsnmp library returns a tuple with all of the data, it is not in any
  way formatted into rows. This function converts the data into a structured
  dictionary, with each key being the MAC address of a wireless client. The
  associated value will be a dictionary containing the information available
  about the client:
      * type        - 1 = sta, 2 = wds
      * rates       - the wireless rates available to the client
      * time        - length of time the client has been connected
      * lastrefresh - time since the client last refreshed
      * signal      - dB signal strength reported by the client (or -1)
      * noise       - dB noise level reported by the client (or -1)
      * rate        - Mb/s rate the client is connected at
      * rx          - number of packets received by the client
      * tx          - number of packets transmitted by the client
      * rxerr       - number of error packets received by the client
      * txerr       - number of error packets transmitted by the client

  Args:
    table: tuple returned from netsnmp
    num: integer number of clients
  Returns:
    dict: {mac_addr: properties_dict}
  """
  table = list(table)
  clients = []
  clientTable = {}

  keys = ['type', 'rates', 'time', 'lastrefresh', 'signal', 'noise',
          'rate', 'rx', 'tx', 'rxerr', 'txerr']

  # First get the MACs
  i = num
  while i > 0:
    data = table.pop(0).lower()
    clients.append(data)
    clientTable[data] = {}
    logging.log(logging.DEBUG, "found client '%s'" % data)
    i = i - 1

  for cmd in keys:
    i = 0
    while i < num:
      data = table.pop(0)
      clientTable[clients[i]][cmd] = data
      i = i + 1

  return clientTable


def GetData(host):
  """Returns a dictionary populated with data about all wireless clients.

  Args:
    host: airport host name
  Returns:
    dict, keyed by mac addr (lowercased)
  """
  wirelessClientTableOID = '.1.3.6.1.4.1.63.501.3.2.2.1'

  numClients = GetNumClients(host)

  if numClients == 0:
    return {}

  logging.log(logging.DEBUG, "polling SNMP for client table")
  clientTable = netsnmp.snmpwalk(netsnmp.Varbind(wirelessClientTableOID), 
                                 Version=2, DestHost=host, 
                                 Community='public')
  clients = TableToDict(clientTable, numClients)

  return clients


if __name__ == '__main__':
  clients = GetData('hoth')
  for client, client_data in clients.iteritems():
    print "%s => %s" % (client, client_data)
