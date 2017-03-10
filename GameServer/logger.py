from queue import Queue
from enum import IntEnum


class LogCodes(IntEnum):

    Network = 0
    Session = 1
    Match = 2
    Ability = 3
    Chance = 4


class Logger:

    logging = True
    log_interval = 250
    queue_count = 5

    _queues = []
    for index in range(0, queue_count):
        _queues.append(Queue())

    @staticmethod
    def log(message, code=LogCodes.Network):

        if Logger.logging:
            Logger._queues[code].put(message)

    @staticmethod
    def log_count(code=LogCodes.Network):
        return Logger._queues[code].qsize()

    @staticmethod
    def retrieve(code=LogCodes.Network):
        return Logger._queues[code].get()
