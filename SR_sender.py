import socket
import math
import time
from threading import Timer


def add_k_bits(msg, seq_bits):
    arr = []
    counter = 0
    for i in range(len(msg)):
        binary_seq = f'{counter:0{seq_bits}b}'
        arr.append(msg[i] + binary_seq)
        counter += 1
        if counter >= math.pow(2, seq_bits):
            counter = 0
    return arr


class Sender:

    def __init__(self, message_arr):
        self.message_arr = message_arr
        self.w = None
        self.k = None
        self.frame_counter = 0
        self.index = -1
        self.last_ack = 0
        self.is_sending = True

        # socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # timer
        self.maxP = 2
        self.p_timer = Timer(2, self.send_RRp1)
        self.timers = []

        # for _ in range(int(math.pow(2, k))):
        #     timer = Timer(6, self.send_RRp1, args=(i,))
        #     self.timers.append(timer)

    def handle_ack(self, ack_message):
        if 'RR' in ack_message:
            seq_num = int(ack_message[2:])
            while self.last_ack is not seq_num:
                self.timers[self.last_ack].cancel()
                self.last_ack = int((self.last_ack + 1) % math.pow(2, self.k))

            print('received ack: \u001b[34m' + ack_message + '\u001b[0m')
            print('last ack:' + str(self.last_ack) + '\n')
            # change frane counter and index
            self.frame_counter = self.last_ack
            t = self.new_count_middles(seq_num)
            self.index = self.index - t

            if not self.is_sending:
                # response to RR(p=1)
                self.p_timer.cancel()
                self.maxP = 2
                self.is_sending = True

        elif 'SREJ' in ack_message:
            seq_num = int(ack_message[4:])
            for timer in self.timers:
                timer.cancel()
            print('received ack: \u001b[31m' + ack_message + '\u001b[0m')
            print('last ack:' + str(self.last_ack) + '\n')
            if not self.is_sending:
                # response to RR(p=1)
                self.p_timer.cancel()
                self.maxP = 2
                self.is_sending = True

            time.sleep(1)
            k = self.new_count_middles(seq_num)
            self.send_msg(self.index - k + 1, seq_num)
            self.receive_ack()

    def new_count_middles(self, seq_num):
        count = seq_num - 1
        last_count = 0
        t = 1
        while count <= self.index:
            last_count = count
            count = t * (math.pow(2, self.k)) + seq_num - 1
            t += 1

        return int(self.index - last_count)

    def set_initial_data(self):
        self.sock.connect(('127.0.0.1', 9090))
        self.k = int(self.sock.recv(1024).decode())
        self.w = int(self.sock.recv(1024).decode())
        for i in range(int(math.pow(2, self.k))):
            timer = Timer(6, self.send_RRp1, args=(i,))
            self.timers.append(timer)

        self.message_arr = add_k_bits(self.message_arr, self.k)
        self.start_sending()

    def start_sending(self):
        print('Ready\n\u001b[31m ============= sender =============\u001b[0m')
        self.sock.settimeout(1.2)

        while self.index < len(self.message_arr) - 1:
            window = [int((self.last_ack + i) % math.pow(2, self.k)) for i in range(self.w)]
            if self.is_sending and self.frame_counter in window:
                self.index += 1
                self.send_msg(self.index, self.frame_counter)
                self.frame_counter = int((self.frame_counter + 1) % math.pow(2, self.k))
                time.sleep(1)

            self.receive_ack()

        self.p_timer.cancel()
        for timer in self.timers:
            timer.cancel()
        self.sock.send('DISC'.encode())
        print('\u001b[31m >>>\u001b[0m sent message:\u001b[34m DISC\u001b[0m')

    def receive_ack(self):
        try:
            msg = self.sock.recv(1024).decode()
        except socket.timeout as e:
            err = e.args[0]
            if err == 'timed out':
                return
        else:
            self.handle_ack(msg)

    def send_msg(self, send_index, frame_index):
        print('\u001b[31m >>>\u001b[0m sent message:{} => F{}'
              .format(self.message_arr[send_index], str(frame_index)))
        self.sock.send(self.message_arr[send_index].encode())
        self.timers[frame_index] = Timer(6, self.send_RRp1, args=(frame_index,))
        self.timers[frame_index].start()

    def send_RRp1(self, index):
        if self.maxP > 0:
            self.is_sending = False
            self.maxP -= 1
            message = 'RR(p=1)'
            for timer in self.timers:
                timer.cancel()

            self.p_timer = Timer(2, self.send_RRp1, args=('p',))
            self.p_timer.start()
            print('send ack: {} => for F{}\n'.format(message, str(index)))
            self.sock.send(message.encode())
        elif self.maxP == 0:
            # to end the main while loop (no response from receiver)
            self.index = len(self.message_arr)


if __name__ == '__main__':
    message_array = ['11111', '11111', '11111', '11111', '11111', '11111', '11111', '11111',
                     '11101', '11101', '11101', '11101', '11101', '11101', '11101', '11101',
                     '11011', '11011', '11011', '11011', '11011', '11011', '11011', '11011',
                     '10111', '10111', '10111', '10111', '10111', '10111', '10111', '10111',
                     '01111', '01111', '01111', '01111', '01111', '01111', '01111', '01111']

    sender = Sender(message_array)
    sender.set_initial_data()
