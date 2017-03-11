import socket as sock
import pymysql
import hashlib
import base64
import re
import binascii

from pymysql.cursors import DictCursor
from logger import Logger
from enum import IntEnum


# Enum to map flag literals to a name
class Flags(IntEnum):

    @staticmethod
    def valid_flag(flag):
        return flag in list(map(int, Flags))

    FAILURE = 0
    SUCCESS = 1
    DRAW = 2
    ERROR = 3
    CLOSE = 8

    ZERO_BYTE = 0
    ONE_BYTE = 1
    TWO_BYTE = 2

    LOGIN = 0
    LOGOUT = 1
    FIND_MATCH = 2
    USER_PROFILE = 3
    ALL_CARDS = 4
    CAT_CARDS = 5
    BASIC_CARDS = 6
    CHANCE_CARDS = 7
    ABILITY_CARDS = 8
    END_MATCH = 9

    OP_CAT = 49
    GAIN_HP = 50
    OP_GAIN_HP = 51
    DMG_MODIFIED = 52
    OP_DMG_MODIFIED = 53
    GAIN_CHANCE = 54
    OP_GAIN_CHANCE = 55
    GAIN_ABILITY = 56
    GAIN_CHANCES = 57
    REVEAL_MOVE = 58
    REVEAL_CHANCE = 59
    SPOTLIGHT = 60
    OP_SPOTLIGHT = 61

    NEXT_PHASE = 98
    READY = 99
    SELECT_CAT = 100
    USE_ABILITY = 101
    SELECT_MOVE = 102
    USE_CHANCE = 103


class Request:

    def __init__(self, flag, token, size, body):

        self.flag = flag
        self.token = token
        self.size = size
        self.body = body


# Helper class that contains useful network functions
class Network:

    # Translates an int to x bytes - returns byte array object
    # byte_f - byte_format
    @staticmethod
    def int_xbyte(num, byte_f):

        _bytes = bytearray()
        for i in range(0, byte_f):

            _bytes.insert(0, num & 0xFF)
            num >>= 8

        return _bytes

    # Determines if the connection is from a WebSocket
    @staticmethod
    def check_wconnection(client):

        is_websocket = False

        # Peek to get data without pulling from queue
        data = (client.recv(1024, sock.MSG_PEEK)).decode('utf-8')

        # If the request is a HTTP GET flush it from the queue and initiate handshake
        if re.search('GET', data):
            is_websocket = True

        return is_websocket

    # Creates response header with flag and size
    @staticmethod
    def generate_responseh(flag, size):

        response = bytearray()
        response.append(flag)
        response += Network.int_xbyte(size, 3)
        return response

    # Creates header with flag and size and attaches response body
    @staticmethod
    def generate_responseb(flag, size, body):

        response = Network.generate_responseh(flag, size)

        if isinstance(body, str):
            response += body.encode('utf-8')
        else:
            response.append(body)

        return response

    # Creates and returns a database connection
    @staticmethod
    def db_connection():
        return pymysql.connect(
            host='69.195.124.204', user='deisume_kittywar',
            password='kittywar', db='deisume_kittywar', autocommit=True)

    # Alternative to db_connection, executes an sql statement for you
    @staticmethod
    def sql_query(query):

        db = Network.db_connection()

        result = None
        # noinspection PyBroadException
        try:
            with db.cursor(DictCursor) as cursor:

                cursor.execute(query)
                result = cursor.fetchall()
        except:
            # print("The following query did not properly execute: " + query)
            Logger.log("The following query did not properly execute: " + query + "\n")

        finally:
            db.close()

        return result

    # Receives a fixed amount of data from client or returns none if error receiving
    @staticmethod
    def receive_data(client, data_size):

        packet = b''
        received_data = bytearray()
        while len(received_data) < data_size:

            try:
                packet = client.recv(data_size - len(received_data))
            except ConnectionResetError:
                pass

            if not packet:
                return None

            received_data += packet

        return received_data

    # Sends a response to client based on previous request
    @staticmethod
    def send_data(username, client, data):

        Logger.log(username + " Response: " + str(data) + "\n")

        # noinspection PyBroadException
        try:
            client.sendall(data)
        except:
            pass

    @staticmethod
    def parse_request(client, data):

        Logger.log("Raw Request: " + str(binascii.hexlify(data)))

        flag = data[0]
        token = data[1:25].decode('utf-8')
        size = int.from_bytes(data[25:28], byteorder='big')

        body = None
        if size > 0:
            body = Network.receive_data(client, size)
            Logger.log("Raw Body: " + str(body) + "\n")

        if body:
            body = body.decode('utf-8')

        request = Request(flag, token, size, body)
        return request


# Helper class that contains useful WebSocket related network functions
class WNetwork(Network):

    @staticmethod
    def handshake(client):

        request = (client.recv(1024)).decode('utf-8')

        response = \
            b'HTTP/1.1 101 Switching Protocols\r\n' \
            b'Upgrade: websocket\r\n' \
            b'Connection: Upgrade\r\n' \
            b'Sec-WebSocket-Accept: %s\r\n\r\n'

        magic_key = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

        match = re.search('Sec-WebSocket-Key: (.*)\r\n', request)
        if match:

            accept_key = (match.group(1) + magic_key).encode('utf-8')
            accept_key = hashlib.sha1(accept_key).digest()
            accept_key = base64.b64encode(accept_key)

            client.sendall(response % accept_key)

    @staticmethod
    def parse_request(client, data):

        payload = WNetwork.read_frame(client, data)
        if not payload:
            return None

        Logger.log("Raw Payload: " + str(payload))

        flag = payload[0]
        token = payload[1:25].decode('utf-8')
        body = payload[25:len(payload)]

        if body:

            Logger.log("Raw Body: " + str(body) + "\n")
            body = body.decode('utf-8')

        # Web Sockets - set size to 0 and ignore
        size = 0

        request = Request(flag, token, size, body)
        return request

    # Creates response header with flag and size
    @staticmethod
    def generate_responseh(flag, size):

        response = WNetwork.write_frame(flag, size)
        return response

    @staticmethod
    def read_frame(client, data):

        decoded_payload = bytearray()
        while True:

            fin = (data[0] & 0x80) >> 7
            opcode = (data[0] & 0x0F)
            mask = (data[1] & 0x80) >> 7
            payload_len = (data[1] & 0x7F)

            Logger.log("Raw Frame: " + str(binascii.hexlify(data)) + "\n" +
                       "Fin: " + str(fin) + "\n" +
                       "Opcode: " + str(opcode) + "\n" +
                       "Mask: " + str(mask) + "\n" +
                       "Payload Length: " + str(payload_len) + "\n")

            if opcode == Flags.CLOSE or payload_len < 25:

                Logger.log("Frame close opcode/Invalid payload length detected" + "\n")
                return None

            if payload_len == 126:
                payload_len = WNetwork.receive_data(client, 2)  # or 0
            elif payload_len == 127:
                payload_len = WNetwork.receive_data(client, 8)  # or 0

            mask_key = WNetwork.receive_data(client, 4)  # or 0
            payload = WNetwork.receive_data(client, payload_len)

            for index in range(len(payload)):
                decoded_payload.append(payload[index] ^ mask_key[index % 4])

            if fin == 1:
                break

            data = WNetwork.receive_data(client, 2)

        return decoded_payload

    @staticmethod
    def write_frame(flag, size):

        response = bytearray()

        # FIN 1 RSVS 000 OPCODE 0010
        # 10000010 - 0x82
        response.append(0x82)

        # iOS code never regarded the flag as body but Web Sockets do!
        # Add one to the size to account for the flag
        size += 1

        # Mask 0
        # Size under or at 7 bit limit
        if size <= 125:
            response.append(size)

        # Size under or at 16 bit limit
        elif size <= 65535:

            response.append(126)
            response += WNetwork.int_xbyte(size, 2)

        # Size will be around 64 bit limit
        else:

            response.append(127)
            response += WNetwork.int_xbyte(size, 8)

        response.append(flag)

        return response
