import logging
import socket

class SignalGenerator:
    """Send SCPI commands to siggen"""
    def __init__(self, addr):
        logging.debug(f"Initing Siggen {addr}")
        self.addr = addr
        self.socket = socket.socket()
        self.socket.connect((self.addr, 5025))

    def send(self, message):
        logging.trace(message)
        self.socket.send(f"{message}\n".encode())

    def trigger(self):
        self.send("TRIG")