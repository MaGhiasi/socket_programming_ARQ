import socket
import math
import time
import random


def initial_data(is_exact, is_random):
    if is_exact == 'Y':
        return [[], [], []]
    if is_random == 'Y':
        crashed_frames = list(set(sorted([random.randint(0, 31) for _ in range(random.randint(2, 15))])))
        crashed_rr = list(set(sorted([random.randint(0, 31) for _ in range(random.randint(2, 15))])))
        crashed_rej = list(set(sorted([random.randint(0, 10) for _ in range(random.randint(2, 10))])))
        return [crashed_frames, crashed_rr, crashed_rej]

    return [[3, 8, 25, 31], [9, 13, 14, 15], [0, 3, 4, 6, 7, 8]]
    # 3 (fr), 0 (rej) => damaged frame then damaged SREJ then frame-time out
    # 8 (fr) => damaged frame
    # 9 (rr) => damaged RR (no problem due to next RR)
    # 13, 14, 15 => consecutive damaged RRs then frame-time out
    # 25 (fr) , 3, 4 (rej) => no response to first Pbit=1
    #                 but response to second Pbit=1 and continue
    # 31 (fr) , 6, 7, 8 (rej) => no response to 2 Pbit=1 in a row and END connection


class Receiver:

    def __init__(self, w, k, crashed_fr_rr_srej):
        self.frame_buffer = []
        self.out_order_buffer = []
        self.crashed_frame_index = []
        self.w = w
        self.k = k
        self.frame_counter = 0
        self.has_rejected = False
        self.counter_fr_rr_srej = [0, 0, 0]
        self.crashed_fr_rr_srej = crashed_fr_rr_srej
        # socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.conn = None

    def initiate_channel(self):
        self.sock.bind(('127.0.0.1', 9090))
        self.sock.listen()
        print('listening')
        self.conn, addr = self.sock.accept()
        self.conn.sendall(str(self.k).encode())
        time.sleep(0.5)
        self.conn.sendall(str(self.w).encode())
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
            if len(self.out_order_buffer) > 0:
                self.send_SREJ(self.counter_fr_rr_srej[2] in self.crashed_fr_rr_srej[2])
            else:
                self.send_RR(False)

        elif 'DISC' in data:    # if packet is a DISC
            print('\n\u001b[31m >>>\u001b[0m received message:' + '\u001b[34m DISC\u001b[0m')

        else:   # if packet is a frame (data)
            seq_number = int(data[-self.k:], 2)
            # Does not receive some specific packets (in not_received_frames)
            if self.counter_fr_rr_srej[0] not in self.crashed_fr_rr_srej[0]:
                print('\n\u001b[31m >>>\u001b[0m received message:' + data)
                self.send_ack(seq_number, data)

            self.counter_fr_rr_srej[0] += 1

    def send_ack(self, seq_num, data):
        if self.frame_counter == seq_num:   # frame with correct sequence number
            self.frame_buffer.append(data)
            self.frame_counter = int((self.frame_counter + 1) % math.pow(2, self.k))

            if self.has_rejected:   # receive crashed frame again
                self.process_out_of_orders()
            else:   # receive normally
                self.send_RR(self.counter_fr_rr_srej[1] in self.crashed_fr_rr_srej[1])

        elif self.frame_counter != seq_num:     # frame with incorrect sequence number
            if self.has_rejected:   # buffering
                self.out_order_buffer.append(data)
            else:   # out of order
                self.has_rejected = True
                self.out_order_buffer.append(data)
                self.send_SREJ(self.counter_fr_rr_srej[2] in self.crashed_fr_rr_srej[2])

    def send_RR(self, is_crashed):
        message = 'RR' + str(self.frame_counter)
        print('send RR: \u001b[34m' + message + '\u001b[0m', end='')
        if not is_crashed:
            self.conn.sendall(message.encode())
            print()
        else:
            print('\u001b[31m \u2718 \u001b[0m')

        self.counter_fr_rr_srej[1] += 1

    def send_SREJ(self, is_crashed):
        message = 'SREJ' + str(self.frame_counter)
        print('send SREJ: \u001b[31m' + message + '\u001b[0m', end='')
        if not is_crashed:
            self.conn.sendall(message.encode())
            print()
        else:
            print('\u001b[31m \u2718 \u001b[0m')

        self.counter_fr_rr_srej[2] += 1

    def process_out_of_orders(self):
        while len(self.out_order_buffer) > 0:
            msg = self.out_order_buffer.pop(0)
            sequence_num = int(msg[-self.k:], 2)

            if self.frame_counter == sequence_num:
                self.frame_buffer.append(msg)
                self.frame_counter = int((self.frame_counter + 1) % math.pow(2, self.k))
            else:
                self.send_SREJ(self.counter_fr_rr_srej[2] in self.crashed_fr_rr_srej[2])
                self.out_order_buffer.insert(0, msg)
                break

        time.sleep(0.5)
        if len(self.out_order_buffer) == 0:
            self.has_rejected = False
            # extra
            self.send_RR(self.counter_fr_rr_srej[1] in self.crashed_fr_rr_srej[1])


if __name__ == '__main__':
    seq_bits = int(input('Enter K: '))
    window_size = int(input('Enter W: '))
    while window_size > math.pow(2, seq_bits-1):
        window_size = int(input(' >>> W out of range\nEnter W: '))

    exact_connection = input('If you want connection without data loss Enter Y,\nelse enter anything: ')
    is_random_loss = 'N'
    if exact_connection != 'Y':
        is_random_loss = input('If you want random data loss Enter Y,\nelse enter anything: ')

    crashed_packets = initial_data(exact_connection, is_random_loss)
    print('> So crashed packets are as follows:\u001b[31;1m\ncrashed data:' + str(crashed_packets[0]) +
          '\ncrashed RR messages:' + str(crashed_packets[1]) +
          '\ncrashed SREJ messages:' + str(crashed_packets[2]) + '\u001b[0m')

    receiver = Receiver(window_size, seq_bits, crashed_packets)
    receiver.initiate_channel()


