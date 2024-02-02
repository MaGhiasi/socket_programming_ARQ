import socket
import math
import time
from threading import Timer


class Sender:

    def __init__(self, message_arr,  w, k):
        self.message_arr = message_arr
        self.w = w
        self.k = k
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
        for i in range(int(math.pow(2, k))):
            timer = Timer(5, self.send_RRp1, args=(i,))
            self.timers.append(timer)

    def handle_ack(self, ack_message):
        if 'RR' in ack_message:
            seq_num = int(ack_message[2:])

            while self.last_ack is not seq_num:
                self.timers[self.last_ack].cancel()
                self.last_ack = int((self.last_ack + 1) % math.pow(2, self.k))

            if not self.is_sending:
                # response to RR(p=1)
                self.index -= self.find_discarded_count()
                self.frame_counter = self.last_ack
                self.p_timer.cancel()
                self.maxP = 2
                self.is_sending = True

        elif 'REJ' in ack_message:
            seq_num = int(ack_message[3:])

            for timer in self.timers:
                timer.cancel()

            self.last_ack = seq_num
            self.index -= self.find_discarded_count()
            self.frame_counter = seq_num
        if 'RR' in ack_message:
            print('received ack: \u001b[34m' + ack_message + '\u001b[0m')
        else:
            print('received ack: \u001b[31m' + ack_message + '\u001b[0m')
        print('last ack:' + str(self.last_ack) + '\n')

    def find_discarded_count(self):
        count = 0
        ack_num = int(self.last_ack)
        while ack_num is not self.frame_counter:
            ack_num = int((ack_num + 1) % (math.pow(2, self.k)))
            count += 1
        return count

    def start_sending(self):
        print('Ready\n\u001b[31m ============= sender =============\u001b[0m')
        self.sock.connect(('127.0.0.1', 8080))
        self.sock.settimeout(1.2)

        while self.index < len(self.message_arr) - 1:
            window = [int((self.last_ack + i) % math.pow(2, self.k)) for i in range(self.w)]

            if self.is_sending and self.frame_counter in window:
                self.index += 1
                self.send_msg(self.index)
                time.sleep(1)

            self.receive_ack()

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

    def send_msg(self, send_index):
        print('\u001b[31m >>>\u001b[0m sent message:{} => F{}'
              .format(self.message_arr[send_index], str(self.frame_counter)))
        self.sock.send(self.message_arr[send_index].encode())
        self.timers[self.frame_counter] = Timer(5, self.send_RRp1, args=(self.frame_counter,))
        self.timers[self.frame_counter].start()
        self.frame_counter = int((self.frame_counter + 1) % math.pow(2, self.k))

    def send_RRp1(self, index):
        if self.maxP > 0:
            self.is_sending = False
            self.maxP -= 1
            message = 'RR(p=1)'
            print('send ack: {} => for F{}\n'.format(message, str(index)))
            self.sock.send(message.encode())
            for timer in self.timers:
                timer.cancel()

            self.p_timer = Timer(2, self.send_RRp1, args=('p',))
            self.p_timer.start()
        elif self.maxP == 0:
            # to end the main while loop (no response from receiver)
            self.index = len(self.message_arr)


if __name__ == '__main__':
    seq_bits = int(input('Enter K: '))
    window_size = int(input('Enter W: '))
    while window_size > math.pow(2, seq_bits) - 1:
        window_size = int(input(' >>> W out of range\nEnter W: '))

    message_array = ['11111', '11111', '11111', '11111', '11111', '11111', '11111', '11111',
                     '11101', '11101', '11101', '11101', '11101', '11101', '11101', '11101',
                     '11011', '11011', '11011', '11011', '11011', '11011', '11011', '11011',
                     '10111', '10111', '10111', '10111', '10111', '10111', '10111', '10111',
                     '01111', '01111', '01111', '01111', '01111', '01111', '01111', '01111']
    counter = 0
    for i in range(len(message_array)):
        binary_seq = f'{counter:0{seq_bits}b}'
        message_array[i] = message_array[i] + binary_seq
        counter += 1
        if counter >= math.pow(2, seq_bits):
            counter = 0

    sender = Sender(message_array, window_size, seq_bits)
    sender.start_sending()
