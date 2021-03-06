#    powernapd plugin - Monitors a UDP socket for data
#
#    Copyright (C) 2011 Canonical Ltd.
#
#    Authors: Dustin Kirkland <kirkland@canonical.com>
#             Andres Rodriguez <andreserl@canonical.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, version 3 of the License.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

import threading, time, socket, os, re, struct, traceback
from logging import error, debug, info, warn

# Obtain MAC address from Monitor Interface
def get_mac_address(iface):
    file = "/sys/class/net/%s/address" % iface
    f = open(file, 'r')
    iface = f.read()
    f.close
    return iface.strip()

# Generate WoL data for local interface to compare with received packet (Partially taken from powerwake)
def get_local_wol_data(mac):
    nonhex = re.compile('[^0-9a-fA-F]')
    mac = nonhex.sub('', mac)
    if len(mac) != 12:
        error("Malformed mac address [%s]" % mac)
    data = ''.join(['FFFFFFFFFFFF', mac * 16])
    wol_data = ''
    for i in range(0, len(data), 2):
        wol_data = ''.join([wol_data, struct.pack('B', int(data[i: i + 2], 16))])
    return wol_data

# Obtain a list of available eth's, with its MAC address and WoL data.
def get_eths_mac_wol_info():
    ifaces = []
    dirs = os.listdir("/sys/class/net")
    for iface in dirs:
        # Obtain MAC address
        mac = get_mac_address(iface)
        # Obtain WoL data of eth
        data = get_local_wol_data(mac)
        ifaces.append({"iface":iface, "mac":mac, "wol":data})
    return ifaces

# Monitor plugin
#   listen for WoL data in a UDP socket. It compares if the data is specifically
#   for any of the interfaces
class WoLMonitor (threading.Thread):

    # Initialise
    def __init__ ( self, config ):
        threading.Thread.__init__(self)
        self._type = config['monitor']
        self._name = config['name']
        self._port = config['port']
        self._host = '' # Bind to all Interfaces
        self._running = False
        self._data_received = False
        self._absent_seconds = 0

    # Start thread
    def start ( self ):
        self._running = True
        threading.Thread.start(self)

    # Stop thread
    def stop ( self ): self._running = False

    # Open port and wait for data (any data will trigger the monitor)
    def run ( self ):
        ifaces = get_eths_mac_wol_info()
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.bind((self._host, self._port))
        except:
            error("Unable to bind port [%s]" % port)
            return
        s.settimeout(5)
        try:
            debug("    WoL monitor started at port [%s]" % self._port)
            while self._running:
                try:
                    recv_wol_msg, address = s.recvfrom(1024)
                    debug("    WoL packet received from %s" % address[0])
                    for iface in ifaces:
                        if recv_wol_msg == iface["wol"]:
                            debug("    WoL data matches local interface [%s]" % iface["iface"])
                            self._data_received = True
                except socket.timeout:
                    pass
        except SystemExit:
            pass

    def active(self):
        if self._data_received:
            self._data_received = False
            return True
        return False

# ###########################################################################
# Editor directives
# ###########################################################################

# vim:sts=4:ts=4:sw=4:et
