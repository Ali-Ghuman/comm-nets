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

    #99,999 
    #1000
    def checkSum(self, data): 
        hashVal = 0
        for char in data:
            hashVal = hashVal*31 + (ord(char) - ord('a'))
        hashVal = str(hashVal % 10000000000)
        return '0' * (10 - len(hashVal)) + hashVal


    def makePacket(self, data, nextseqnum): 
        paddedSeqNum = '0' * (5 - len(str(nextseqnum))) + str(nextseqnum)
        checkSum = self.checkSum(str(data) + paddedSeqNum)
        return data + bytearray(paddedSeqNum + checkSum, 'utf-8')
        

    def resend(self, data): 
        self.timer = Timer(self.timeout, self.resend, [data])
        self.timer.daemon = True 
        self.timer.start()
        for i in range(self.base, self.nextseqnum):
            self.simulator.u_send(self.makePacket(data[i], i))

        sys.exit(0)

    def send(self, data): 
        packets = []
        for i in range(0, len(data), self.packetSize):
            packets.append(data[i:i + self.packetSize])
        while True: 
            try: 
                if self.base == len(packets): # if we receive all the ACKs
                    break

                if self.nextseqnum < self.base + self.N and self.nextseqnum < len(packets): 
                    packet = self.makePacket(packets[self.nextseqnum], self.nextseqnum)
                    self.simulator.u_send(packet)

                    if self.base == self.nextseqnum:
                        self.timer = Timer(self.timeout, self.resend, [packets])
                        self.timer.daemon = True 
                        self.timer.start()
                    self.nextseqnum += 1
            except socket.timeout:
                sys.exit()
            
            try: 
                ack = self.simulator.u_receive()  

                if str(ack[-10:]) == self.checkSum(str(ack[:-10])):
                    ack_value = int(str(ack[:-10]))
                    self.base = ack_value + 1

                    if self.base == self.nextseqnum:
                        self.timer.cancel()
                    else: 
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
