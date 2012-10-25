import socket
from . import helping_functions
import functools
import logging
import time
import json

import tornado.ioloop
import random
try:
    import d2p.core.bootstrap
except ImportError as e:
    pass

class MulticastBootstrap():
    bootstrap_type = 'multicast'
    ui_bootstrap_name = 'Multicast bootstrap'
    
    _bootstrap_msg = "bootstrap"
    _bootstrap_answer = "bootstrap_answer"
    _bootstrap_port = 8778
    _mcast_ip = "224.0.1.190" 
    
    # generated from python3 """hashlib.md5("anton.die.ente".encode("utf-8")).hexdigest()"""
    _magic_string = "6e5ebb3cbbfdbc0dada950e87bf2a342"

    def __init__(self):
        self._old_interfaces = []
        
        self._countPeriod = -1
        self._periodNumber = 10
        self._isBsRunning = False
        self._lastActivBsTime = ""
    
    
    def start(self, assignedId, io_loop, getAdvertised, onFind):
        """ Start running on the specified io_loop """
        self.ioloop = io_loop
        self.assignedId = assignedId
        self._getAdvertised = getAdvertised
        self._onFind = onFind
        self._entries = []
        
        self._socket = self._createSocket()
        self.ioloop.add_handler(self._socket.fileno(), self._receivedMsgHandler, self.ioloop.READ)

        self._p_if_c = tornado.ioloop.PeriodicCallback(self._checkInterfaces, 1000, io_loop = self.ioloop)
        self._p_if_c.start()
        self._pms = tornado.ioloop.PeriodicCallback(self._sendBsMsgHandler, 1000, io_loop = self.ioloop)
        #self.ui_startPeriod_send_bs(5)
        
        
    def ui_addEntry(self, bse):
        assert bse.addr
        #self._entries.append(bse)
        self._onFind(bse)
        
    @property
    def ui_entries(self):
        return self._entries
        
    def ui_last_activ_bs_ts(self):
        return self._lastActivBsTime

    def ui_is_running(self):
        return self._isBsRunning
        
    def ui_startPeriod_send_bs(self, periodNumber=3):
        self._periodNumber = periodNumber
        self._pms.stop() # First stop the PeriodicCallback then start. Otherwise several PMC will send bs_msg parallel
        self._countPeriod = 0
        self._pms.start()
        self._isBsRunning = True

    def ui_start_send_bs(self):
        """Start sending multicast bootstrap messages"""
        self._countPeriod = -1
        self._pms.stop() # First stop the PeriodicCallback then start. Otherwise several PMC will send bs_msg parallel
        self._pms.start()
        self._isBsRunning = True

    def ui_stop_send_bs(self):
        """Start sending multicast bootstrap messages"""
        self._pms.stop()
        self._countPeriod = -1
        self._isBsRunning = False

    def _checkInterfaces(self):
        """This method will be called periodicaly and checks if new interfaces are available or old interfaces lost.
        If a new is available then one multicast reveiver and one multicast sender socket for this interface will created."""
        new_interfaces = self._searchSuitableInterfaces()
        if len(self._old_interfaces) == 0:
            self._old_interfaces = new_interfaces
            for new_if in new_interfaces:
                self._socket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, socket.inet_aton(self._mcast_ip) + socket.inet_aton(new_if[1]))

        else:
            # Look if new found interfaces are already known. If not then add the new interfaces.
            for new_if in new_interfaces:
                if all(new_if[0] != old_if[0] for old_if in self._old_interfaces):
                    self._socket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, socket.inet_aton(self._mcast_ip) + socket.inet_aton(new_if[1]))
                    self._old_interfaces.append(new_if)

            # Look if old interfaces are still available. If not then remove the old interfaces.
            for old_if in self._old_interfaces:
                if all(new_if[0] != old_if[0] for new_if in new_interfaces):
                    self._socket.setsockopt(socket.IPPROTO_IP, socket.IP_DROP_MEMBERSHIP, socket.inet_aton(self._mcast_ip) + socket.inet_aton(old_if[1]))
                    self._old_interfaces.remove(old_if)


    def _searchSuitableInterfaces(self, interfaces_blacklist = ["lo"]):
        """ This method returns a list of available network interfaces.
        If one of the interfaces is contained in the blacklist, then do not use this interface.
        @return : returns interfaces that can used for a multicast bootstrap.
        """
        active_interfaces = []
        up_if_and_ip = helping_functions.get_up_ifs_and_ip()
        for up_if in up_if_and_ip:
            if up_if[0] not in interfaces_blacklist:
                active_interfaces.append(up_if)
        return active_interfaces


    def _createSocket(self):
        """This method creates a ipv4 multicast udp socket"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR,1)
        sock.bind(("", self._bootstrap_port))
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 3)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 0)
        sock.setblocking(0)
        return sock
        
        
    def _receivedMsgHandler(self, fd, events):
        try:
            data, addr = self._socket.recvfrom(1024)
        except socket.error as e:
            pass
        data_str = data.decode("UTF-8")
        self._handleReceivedMsg(data_str, addr)


    def _handleReceivedMsg(self, msg, addr):
        """This method checks which message type was received and how to react to this message.
        @param msg: the received data.
        @type msg: A String read from a socket.
        @param addr: The unicast host and senderport from the sender.
        @type addr: list
        """
        if msg.startswith(self._magic_string):
            jsonData = json.loads(msg[len(self._magic_string):])
            if jsonData["MSG_TYPE"] == self._bootstrap_msg:
                dest_addr = (addr[0], self._bootstrap_port)
                self._sendBootstrapAnswer(dest_addr)
                
            if jsonData["MSG_TYPE"] == self._bootstrap_answer:
                self._notifyMember("p2p-ipv6-tcp", addr[0], int(jsonData["DATA"]["TRANSPORT_PORT"]))


    def _sendBsMsgHandler(self):
        """This method send over all available interfaces a bootstrap message."""
        if self._countPeriod >= self._periodNumber:
            self.ui_stop_send_bs()
        if self._countPeriod in range(self._periodNumber):
            self._countPeriod = self._countPeriod + 1
            
        bootstrapMsg = self._createBsMsg()
        for old_if in self._old_interfaces:
            utf8_coded_msg = bytes(bootstrapMsg, "UTF-8")
            dest_addr = (self._mcast_ip, self._bootstrap_port)
            try:
                self._socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton(old_if[1]))
                self._socket.sendto(utf8_coded_msg, dest_addr)
            except socket.error as e:
                print("Sending Bootstrap MSG socket.error")
            self._lastActivBsTime = time.asctime()


    def _sendBootstrapAnswer(self, dest_addr):
        """This method answers to the multicast bootstrap message of a new member with a unicast datagram packet.
        @param newMember: This Member object contains all relevant informations like host, port or MID of the new member.
        @type newMember: A Member object
        """
        transport_infos = self._getAdvertised()
        transport_port = transport_infos[0].port

        informations = {"TRANSPORT_PORT" : transport_port}
        bs_answer = self._getHighestWrapperMsg(self._bootstrap_answer , informations)
        data_bytes = bytes(bs_answer, "UTF-8")
        self._socket.sendto(data_bytes, dest_addr)



    def _getHighestWrapperMsg(self, msg_type, data=""):
        """This is the highest wrapper msg with all relevant informations for identification, assignement and data transport.
            @param msg_type: Defines the message type.
            @param data: The data witch should send with the message wrapper. Default is a blank String.
            @return: dict
        """
        data_part = {"MSG_TYPE":msg_type, "DATA":data}
        data_part = json.dumps(data_part)
        return self._magic_string+data_part
    
    def _createBsMsg(self):
        """This method generates a bootstrap message to sending over the multicast sockets.
        Therefore the relevant infos will wrapped and dumps to a json datastructure.
        @return : Informations wrapped in a dict, converted to a json datastructure
                 and dumps to a string for sending over a socket.
        """
        transport_infos = self._getAdvertised()
        transport_port = transport_infos[0].port
        data_part = {"TRANSPORT_PORT" : transport_port, "RANDOMNUM" : round(random.random()*1000)}
        bs_msg = self._getHighestWrapperMsg(self._bootstrap_msg, data_part)
        return bs_msg

    def _notifyMember(self, transportId, addr, port):
        """Create the BootstrapEntry namedtuple, set the data and call the addEntry method from d2p"""
        bse = d2p.core.bootstrap.BootstrapEntry
        bse.transportId = transportId
        bse.addr = addr
        bse.addr = "::ffff:"+addr
        bse.port = port
        self.ui_addEntry(bse)






import collections
BootstrapEntry = collections.namedtuple('BootstrapEntry',
                                         ['transportId',
                                          'addr', # IP (or similar) address. None for automatic detection
                                          'port' # Extended information like port
                                         ])

def getAdvertised():
    return [BootstrapEntry("p2p-ipv6-tcp", None, 48865)]
    
def addEntry(bse):
    print("Add Entry!!!")
    return

def main():
    print("Multicast Bootstrap started")
    io_loop = tornado.ioloop.IOLoop()
    mbs = MulticastBootstrap()
    mbs.start(io_loop, getAdvertised, addEntry)
    mbs.ui_start_send_bs()
    io_loop.start()
    
