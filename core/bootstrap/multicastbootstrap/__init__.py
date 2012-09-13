import socket
from . import helping_functions
import functools
import logging
import time
import json

import tornado.ioloop
import random
import d2p.core.bootstrap


class MulticastBootstrap():
    BOOTSTRAP_MSG = "bootstrap"
    BOOTSTRAP_ANSWER = "bootstrap_answer"
    BOOTSTRAP_PORT = 8778
    MCAST_IP = "224.168.2.9"
    # generated from "uniduesseldorf,valerij" with sha1 on the website http://www.php-einfach.de/sonstiges_generator_md5.php
    PID = "144c3010108b2b6c1a39f589722c0aef97af1982" 
    
    def __init__(self, ioloop, getAdvertised, addEntry):
        self.ioloop = ioloop
        self._getAdvertised = getAdvertised
        self.addEntry = addEntry
        self.MyMID = self._createMyMID()

        self._interface_sockets = [] # list of namedtupels with interface name and receiv_
        
        callback = functools.partial(self._checkInterfaces)
        self._p_if_c = tornado.ioloop.PeriodicCallback(callback, 1000, io_loop = self.ioloop)
        self._p_if_c.start()

        callback = functools.partial(self._sendBsMsgHandler)
        self._pms = tornado.ioloop.PeriodicCallback(callback, 2000, io_loop = self.ioloop)
        #self.set_bootstrapping("start")
        
    
    def set_bootstrapping(self, action):
        """This method will be called from the ui and start and stop the multicast bootstrap sender. """
        if action == "stop":
            self._pms.stop()
        elif action == "start":
            self._pms.stop()
            self._pms.start()

    
    def _checkInterfaces(self):
        """This method will be called periodicaly and checks if new interfaces are available or old interfaces lost.
        If a new is available then one multicast reveiver and one multicast sender socket for this interface will created."""
        new_interfaces = self._searchSuitableInterfaces()  
        if len(self._interface_sockets) == 0:
            for new_if in new_interfaces:
                ifname_sock = (new_if[0], self._createSocket(new_if[1]), self._createSenderSocket(new_if[1]))
                #ifname_sock = (new_if[0], self._createSocket("0.0.0.0"), self._createSenderSocket("0.0.0.0"))
                self._interface_sockets.append(ifname_sock)
                
                # Add the new reveiver socket to the ioloop handler
                callback = functools.partial(self._receivedMsgHandler, ifname_sock[1])
                self.ioloop.add_handler(ifname_sock[1].fileno(), callback, self.ioloop.READ)
        else:           
            # Look if new found interfaces are already known
            for new_if in new_interfaces:
                already_contained = False
                for old_if in self._interface_sockets:
                    if new_if[0] == old_if[0]:
                        already_contained = True
                        break
                if not already_contained:
                    
                    ifname_sock = (new_if[0], self._createSocket(new_if[1]), self._createSenderSocket(new_if[1]))
                    #ifname_sock = (new_if[0], self._createSocket("0.0.0.0"), self._createSenderSocket("0.0.0.0"))
                    
                    # Add the new reveiver socket to the ioloop handler
                    callback = functools.partial(self._receivedMsgHandler, ifname_sock[1])
                    self.ioloop.add_handler(ifname_sock[1].fileno(), callback, self.ioloop.READ)
                    
                    self._interface_sockets.append(ifname_sock)
                        
            # Look if old interfaces are still available
            for old_if in self._interface_sockets:
                is_present = False
                for new_if in new_interfaces:  
                    if  new_if[0] == old_if[0]:
                        is_present = True
                        break      
                if not is_present:
                    fd = old_if[1].fileno()
                    self.ioloop.remove_handler(fd)
                    self._interface_sockets.remove(old_if)
                    
                    
    def _searchSuitableInterfaces(self, interfaces_blacklist = ["lo"]):
        """ This method returns a list of available network interfaces. 
        If one of the interfaces is contained in the blacklist, then this interface will not used
        @return : returns interfaces that can used for a multicast bootstrap.
        """
        active_interfaces = []
        up_if_and_ip = helping_functions.get_up_ifs_and_ip()
        for up_if in up_if_and_ip:
            if up_if[0] not in interfaces_blacklist:
                active_interfaces.append(up_if)
        return active_interfaces


    def _createSocket(self, up_if_ip=""):
        """This method creates a ipv4 multicast udp socket"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR,1)
        sock.bind(("", self.BOOTSTRAP_PORT))
        
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 3)
        
        #Tell the kernel that we want to listen on multicast packets. Add to a multicast group.
        #The up_if_ip is important if the device is an AP or in wi-fi direct mode, else the socket do not know on which interfaces will come multicast packets.
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, socket.inet_aton(self.MCAST_IP) + socket.inet_aton(up_if_ip))
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton(up_if_ip)) #If send multicast packets this is importand to for the socket to know if AP.
        sock.setblocking(1)
        return sock       
        
        
    def _createSenderSocket(self, up_if_ip=""):
        """This method creates a ipv4 multicast udp socket for sending multicast udp packets"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            #sock.bind(('', self.BOOTSTRAP_PORT))
            
            #sock.setsockopt(socket, IPPROTO_IP, IP_MULTICAST_LOOP, 1, 1) #Enable or disable loopback
            
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 3) # Set the hop count
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton(up_if_ip))
        except socket.error as e:
            return False
        return sock      


    def _receivedMsgHandler(self, sock, fd, events):
        try:
            data, addr = sock.recvfrom(1024)
            data_str = data.decode("UTF-8")
            self._handleReceivedMsg(sock, data_str, addr)
        except socket.error as e:
            #self.ioloop.remove_handler(fd)
            logging.error("Exception in MulticastBootstrap _receivedMsgHandler")
            ############# DEBUG #############
            helping_functions.print_msg_for_debug("BOOTSTRAP_MSG receiving FAULT")
            ################################


    def _handleReceivedMsg(self, sock, data, addr):
        """This method checks which message type was received and how to react to this message.
        @param data: the received data.
        @type data: A String read from a socket.
        @param addr: The unicast host and senderport from the sender.
        @type addr: list
        """
        is_data_valid = self._isDataValid(data)
        if is_data_valid is not False:
            jsonData = is_data_valid
            if jsonData["MSG_TYPE"] == self.BOOTSTRAP_MSG:
                #self._notifyMember("p2p-ipv6-tcp", addr[0], int(jsonData["DATA"]["TRANSPORT_PORT"])) # Währe ein Angrifspunkt für die Anwendung
                dest_addr = (addr[0], jsonData["DATA"]["PORT"])
                TEMP_INFO = jsonData["DATA"]["RANDOMNUM"]
                self._sendBootstrapAnswer(sock, dest_addr, TEMP_INFO)
                ############ DEBUG #############
                helping_functions.print_msg_for_debug("BOOTSTRAP_MSG received ## "+" Zufallszahl " + str(jsonData["DATA"]["RANDOMNUM"]))
                ################################
            if jsonData["MSG_TYPE"] == self.BOOTSTRAP_ANSWER:
                self._notifyMember("p2p-ipv6-tcp", addr[0], int(jsonData["DATA"]["TRANSPORT_PORT"]))
                ############ DEBUG #############
                helping_functions.print_msg_for_debug("BOOTSTRAP_ANSWER received from " +addr[0]+ " RE_Zufallszahl " +str(jsonData["DATA"]["RANDOMNUM"]))
                ################################


    def _sendBsMsgHandler(self):
        """This method send over all available interfaces an bootstrap message."""
        bootstrapMsg = self._createBsMsg()

        for element in self._interface_sockets:
            #sender_socket = element[2]
            sender_socket = element[1]
            utf8_coded_msg = bytes(bootstrapMsg, "UTF-8")
            dest_addr = (self.MCAST_IP, self.BOOTSTRAP_PORT)
            try:
                sender_socket.sendto(utf8_coded_msg, dest_addr)
                ############# DEBUG #############
                temp = json.loads(bootstrapMsg)
                zufallszahl = temp["DATA"]["RANDOMNUM"]
                helping_functions.print_msg_for_debug("BOOTSTRAP sended  IF:"+ str(element[0]) + " SE_Zufallszahl " + str(zufallszahl))
                #################################
            except socket.error as e:
                logging.error("BOOTSTRAP_MSG sended FAULT in McastBootstrapSender")
                ############# DEBUG #############
                helping_functions.print_msg_for_debug("BOOTSTRAP_MSG sended FAULT in McastBootstrapSender")
                #################################
        if len(self._interface_sockets) == 0:
            ############# DEBUG #############
            helping_functions.print_msg_for_debug("Available interfaces: " + self._interface_sockets.__str__())
            #################################    

    def _sendBootstrapAnswer(self, sock, dest_addr, TEMP_INFO):
        """This method answers to the multicast bootstrap message of a new member with a unicast datagram packet.
        @param newMember: This Member object contains all relevant informations like host, port or MID of the new member.
        @type newMember: A Member object
        """   
        #for sender_sock in self._interface_sockets:
        #    sock = sender_sock[2]
        transport_infos = self._getAdvertised()
        transport_port = transport_infos[0].port
        
        informations = {"PORT" : self.BOOTSTRAP_PORT, "TRANSPORT_PORT" : transport_port, "RANDOMNUM" : TEMP_INFO}
        bootstrap_answer = self._getHighestWrapperMsg(self.BOOTSTRAP_ANSWER, informations)
        dataToSend = json.dumps(bootstrap_answer)
        data_bytes = bytes(dataToSend, "UTF-8")
        
        sock.sendto(data_bytes, dest_addr)
        
        ########### Debug ##############
        helping_functions.print_msg_for_debug("BOOTSTRAP_MSG answered to  " + str(dest_addr[0]) + " : "+ str(dest_addr[1]) +" Zufallszahl "+ str(TEMP_INFO))     
        print("-------------------")
        ################################
    
    def _getHighestWrapperMsg(self, msg_type, data=""):
        """This is the highest wrapper msg with all relevant informations for identification, assignement and data transport.
            @param msg_type: Defines the message type.
            @param data: The data witch should send with the message wrapper. Default is a blank String.
            @return: dict
        """
        return {"PID":self.PID, "MID":self.MyMID, "MSG_TYPE":msg_type, "DATA":data}
    
    def _createBsMsg(self):
        """This method generates a bootstrap message to sending over the multicast sockets.
        Therefore the relevant infos will wrapped and dumps to a json datastructure.
        @return : Informations wrapped in a dict, converted to a json datastructure
                 and dumps to a string for sending over a socket.
        """
        transport_infos = self._getAdvertised()
        transport_port = transport_infos[0].port
        data_part = {"PORT" : self.BOOTSTRAP_PORT, "TRANSPORT_PORT" : transport_port, "RANDOMNUM" : round(random.random()*1000)}
        bootstrap_msg = self._getHighestWrapperMsg(self.BOOTSTRAP_MSG, data_part)
        return json.dumps(bootstrap_msg)

    def _notifyMember(self, transportId, addr, port):
        """Create the BootstrapEntry namedtuple, set the data and call the addEntry method from d2p"""
        bse = d2p.core.bootstrap.BootstrapEntry
        bse.transportId = transportId
        bse.addr = addr
        bse.addr = "::ffff:"+addr
        print(bse.addr)
        bse.port = port
        self.addEntry(bse)
    
    def _isDataValid(self, data):
        """This method checks if the received data packet is valid and aimed to this program. If yes then return the data as jsonData else return False
        @param data: The data that should checked on validity.
        @type data: String readed from the socket.
        @return: boolean socket data converted to json string if valid and False if not aimed to this program.
        """
        jsonData = json.loads(data)
        if jsonData["PID"] == self.PID: # Check if it is the right protocol
            if jsonData["MID"] != self.MyMID: # Check if message is my own bootstrap msg # TODO: Ist das notwendig???
                return jsonData
        return False             
  
    def _createMyMID(self):
        """Creates a random member id..
        With this id other peers in the network can see if the received msg is comming from another peer.
        @return: Random generated integer."""
        return round(random.random()*100000000) 
        
              
                    
if __name__ == "__main__":
    print("Receiving started")
    #McastBootstrapReceiver()        
