# Written by S. Mevawala, modified by D. Gitzel

import logging

import channelsimulator
import utils
import sys
import socket


class Receiver(object):

    def __init__(self, inbound_port=50005, outbound_port=50006, timeout=10, debug_level=logging.INFO):
        self.logger = utils.Logger(self.__class__.__name__, debug_level)

        self.inbound_port = inbound_port
        self.outbound_port = outbound_port
        self.simulator = channelsimulator.ChannelSimulator(inbound_port=inbound_port, outbound_port=outbound_port,
                                                           debug_level=debug_level)
        self.simulator.rcvr_setup(timeout)
        self.simulator.sndr_setup(timeout)

    def receive(self):
        raise NotImplementedError(
            "The base API class has no implementation. Please override and add your own.")


class BogoReceiver(Receiver):
    ACK_DATA = bytes(123)

    def __init__(self):
        super(BogoReceiver, self).__init__()

    def receive(self):
        self.logger.info("Receiving on port: {} and replying with ACK on port: {}".format(
            self.inbound_port, self.outbound_port))
        while True:
            try:
                data = self.simulator.u_receive()  # receive data
                # note that ASCII will only decode bytes in the range 0-127
                self.logger.info(
                    "Got data from socket: {}".format(data.decode('utf-8')))
                sys.stdout.write(data)
                self.simulator.u_send(BogoReceiver.ACK_DATA)  # send ACK
            except socket.timeout:
                sys.exit()

class RealReceiver(Receiver):
    def __init__(self):
        super(RealReceiver, self).__init__()
    
    expectedseqnum = 0

    def checkSum(self, data): 
        hashVal = 0
        for char in data:
            hashVal = hashVal*31 + (ord(char) - ord('a'))
        hashVal = str(hashVal % 10000000000)
        return '0' * (10 - len(hashVal)) + hashVal

    def receive(self):
        self.logger.info("Receiving on port: {} and replying with ACK on port: {}".format(self.inbound_port, self.outbound_port))

        while True: 
            try:    
                data = self.simulator.u_receive() 
                seqnumreceived = data[-15:-10]

                if data[-10:] == self.checkSum(str(data[:-10])): 
                    seqnumdecoded = int(seqnumreceived.decode())

                    if self.expectedseqnum == seqnumdecoded:
                        sys.stdout.write(data[:-15])
                        seqchecksum = self.checkSum(str(seqnumreceived))
                        self.simulator.u_send(bytes(str(seqnumreceived) + seqchecksum))  
                        self.logger.info("SeqNumReceived {}, Decoded {} ".format(seqnumreceived, seqchecksum))
                        self.expectedseqnum += 1

                    else: 
                        repeatAck = str(self.expectedseqnum - 1)
                        seqchecksum = self.checkSum("0" * (5-len(repeatAck)) + repeatAck)
                        self.simulator.u_send(bytearray(repeatAck + seqchecksum, encoding="utf8"))  
                else: 
                    continue
                
            except socket.timeout:
                sys.exit()

if __name__ == "__main__":
    # test out BogoReceiver
    rcvr = RealReceiver()
    rcvr.receive()
