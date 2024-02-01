import socket
import math


class Receiver:

    def __init__(self, w, k):
        self.frame_buffer = []
        self.w = w
        self.k = k
        self.last_ack = 0
        self.frame_counter = 0
        self.has_rejected = False
        self.controller_count = 0
        self.not_received_frames = [3, 12]
        self.no_rr_frames = [6, 7, 8, 15]
        self.no_rej_frames = [12]
        # socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.conn = None

    def initiate_channel(self):
        self.sock.bind(('127.0.0.1', 8080))
        self.sock.listen()
        print('listening')
        self.conn, addr = self.sock.accept()
        self.receive()

    def receive(self):
        print('\u001b[31m ============= receiver =============\u001b[0m', end='')
        data = ''
        while data != 'DISC':
            data = self.conn.recv(1024).decode()
            self.detect_message(data)

    def detect_message(self, data):
        if 'RR' in data:    # if packet is RR(pbit=1)
            print('\n\u001b[31m >>>\u001b[0m received message:' + data)
            self.send_RR(False)

        elif 'DISC' in data:    # if packet is a frame (data)
            print('\n\u001b[31m >>>\u001b[0m received message:' + '\u001b[34m DISC\u001b[0m')
        else:
            # Does not receive some specific packets (in not_received_frames)
            if self.controller_count not in self.not_received_frames:
                print('\n\u001b[31m >>>\u001b[0m received message:' + data)

                self.last_ack = ((self.last_ack + 1) % (math.pow(2, self.k)))
                seq_number = int(data[-3:], 2)
                self.send_ack(seq_number, data)
            elif not self.has_rejected:
                self.controller_count += 1

    def send_ack(self, seq_num, data):
        if self.frame_counter == seq_num:
            self.frame_buffer.append(data)
            self.controller_count = len(self.frame_buffer)
            self.frame_counter = int((self.frame_counter + 1) % math.pow(2, self.k))
            self.has_rejected = False
            self.send_RR(self.controller_count - 1 in self.no_rr_frames)

        # to discard others after rejection (if seq num is not correct)
        elif not self.has_rejected:
            self.send_REJ((self.controller_count-1) in self.no_rej_frames)
            self.has_rejected = True

    def send_RR(self, is_crashed):
        message = 'RR' + str(self.frame_counter)
        print('send RR: \u001b[34m' + message + '\u001b[0m', end='')
        if not is_crashed:
            self.conn.sendall(message.encode())
            print()
        else:
            print('\u001b[31m \u2718 \u001b[0m')

    def send_REJ(self, is_crashed):
        message = 'REJ' + str(self.frame_counter)
        print('send REJ: \u001b[31m' + message + '\u001b[0m', end='')
        if not is_crashed:
            self.conn.sendall(message.encode())
            print()
        else:
            print('\u001b[31m \u2718 \u001b[0m')


if __name__ == '__main__':
    seq_bits = int(input('Enter k: '))
    window_size = int(input('Enter W: '))
    receiver = Receiver(window_size, seq_bits)
    receiver.initiate_channel()
