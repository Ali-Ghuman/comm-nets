# Written by S. Mevawala, modified by D. Gitzel

import logging
import socket

import channelsimulator
import utils
import sys
from threading import Timer

class Sender(object):

    def __init__(self, inbound_port=50006, outbound_port=50005, timeout=10, debug_level=logging.INFO):
        self.logger = utils.Logger(self.__class__.__name__, debug_level)

        self.inbound_port = inbound_port
        self.outbound_port = outbound_port
        self.simulator = channelsimulator.ChannelSimulator(inbound_port=inbound_port, outbound_port=outbound_port,
                                                           debug_level=debug_level)
        self.simulator.sndr_setup(timeout)
        self.simulator.rcvr_setup(timeout)

    def send(self, data):
        raise NotImplementedError("The base API class has no implementation. Please override and add your own.")


class BogoSender(Sender):

    def __init__(self):
        super(BogoSender, self).__init__()

    def send(self, data):
        self.logger.info("Sending on port: {} and waiting for ACK on port: {}".format(self.outbound_port, self.inbound_port))
        while True:
            try:
                self.simulator.u_send(data)  # send data
                ack = self.simulator.u_receive()  # receive ACK
                self.logger.info("Got ACK from socket: {}".format(
                    ack.decode('ascii')))  # note that ASCII will only decode bytes in the range 0-127
                break
            except socket.timeout:
                pass

        
class RealSender(Sender):

    def __init__(self):
        super(RealSender, self).__init__()

    # N = 100
    N = 4
    base = 0 
    nextseqnum = 0
    timeout = 0.10
    packetSize = 10
    timer = Timer(1, 1)

    # used to make sure that the packet has no errors after transmission
    def checkSum(self, data): 
        hashVal = 0
        for char in data:
            hashVal = hashVal*31 + (ord(char) - ord('a'))
        hashVal = str(hashVal % 10000000000) #make sure the length of the string is 10
        return '0' * (10 - len(hashVal)) + hashVal #zero pad for convenience


    def makePacket(self, data, nextseqnum):  #function to make the packet to send 
        paddedSeqNum = '0' * (5 - len(str(nextseqnum))) + str(nextseqnum) 
        # the largest number is 99,999 which is 5 digits, so make sure the seq is always 
        # 5 digits for convenience 

        checkSum = self.checkSum(str(data) + paddedSeqNum) #get a checksum of the data + seq
        return data + bytearray(paddedSeqNum + checkSum, 'utf-8') #the packet we want to send
        

    def resend(self, data): 
        self.timer = Timer(self.timeout, self.resend, [data]) 
        # set up a new timer to resend the data 
        self.timer.daemon = True  # used to make sure the thread dies
        self.timer.start() # start the timer 

        # using go-back-N, send all the data from base to nextseqnum
        for i in range(self.base, self.nextseqnum): 
            self.simulator.u_send(self.makePacket(data[i], i))

        sys.exit(0)

    def send(self, data): 
        packets = []
        # split up the data into packetsized pieces
        for i in range(0, len(data), self.packetSize):
            packets.append(data[i:i + self.packetSize])

        while True: 
            try: 
                if self.base == len(packets): # if we receive all the ACKs we're done
                    break

                # if we're not finished, make a packet and send it
                if self.nextseqnum < self.base + self.N and self.nextseqnum < len(packets): 
                    packet = self.makePacket(packets[self.nextseqnum], self.nextseqnum)
                    self.simulator.u_send(packet)

                    # used to set up the timer if proper conditions are met 
                    if self.base == self.nextseqnum:
                        self.timer = Timer(self.timeout, self.resend, [packets])
                        self.timer.daemon = True 
                        self.timer.start()
                    self.nextseqnum += 1 #update the sequence number
            except socket.timeout:
                sys.exit()
            
            try: 
                ack = self.simulator.u_receive() # wait to receive the packet 

                # check the checksum of the ack received 
                if str(ack[-10:]) == self.checkSum(str(ack[:-10])):
                    ack_value = int(str(ack[:-10])) #get the ack value 
                    self.base = ack_value + 1 # update the base value w the new ack value

                    if self.base == self.nextseqnum: # cancel the timer
                        self.timer.cancel()
                    else: # resend the packet if it's out of order
                        self.timer.cancel()
                        self.timer = Timer(self.timeout, self.resend, [packets])
                        self.timer.daemon = True 
                        self.timer.start()     
                else: 
                    continue
            except socket.timeout:
                sys.exit()


if __name__ == "__main__":
    # test out BogoSender
    DATA = bytearray(sys.stdin.read())
    sndr = RealSender()
    sndr.send(DATA)
