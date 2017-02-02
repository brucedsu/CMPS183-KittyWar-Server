#!/usr/bin/python3
# Kitty War game server
# TCP Port 2056

import socket as sock
import tkinter
import tkinter.scrolledtext

from network import Network
from sessions import Session
from match import Match, Player
from threading import Thread, Event
from queue import Queue
from logger import Logger

server_running = True


def main():

    # Create server
    server = sock.socket(sock.AF_INET, sock.SOCK_STREAM)
    server_address = ('localhost', 2056)

    # Prepare lobby and match making thread
    match_event = Event()
    lobby = Queue()

    # Start match making thread
    matchmaker_thread = Thread(target=match_maker, args=(match_event, lobby))
    matchmaker_thread.daemon = True
    matchmaker_thread.start()

    # Bind server and listen for clients
    server.setsockopt(sock.SOL_SOCKET, sock.SO_REUSEADDR, 1)
    server.bind(server_address)
    server.settimeout(1)
    server.listen(5)

    # Grab all basic game information(cards) and store in GameThread to prevent
    # repeatedly pulling this information for each session on request
    card_information = pull_card_data()

    # Set global Session variables for debugging/matchmaking/information to apply to all sessions
    Session.card_information = card_information
    Session.lobby = lobby
    Session.match_event = match_event

    # Create thread dedicated to listening for clients
    polling_thread = Thread(target=poll_connections, args=(server,))
    polling_thread.daemon = True
    polling_thread.start()

    # Server GUI code
    root = tkinter.Tk()
    root.geometry("600x600")
    root.title("KittyWar Game Server")

    # Create text display
    server_display = tkinter.scrolledtext.ScrolledText(root)
    server_display.config(state=tkinter.DISABLED)
    server_display.pack()

    # Create shutdown button
    shutdown_button = tkinter.Button(root, text="Shutdown Server", command=shutdown_server)
    shutdown_button.pack()

    # Start GUI and set update to every 100ms
    root.after(100, update_display, (root, server_display))
    root.mainloop()


def pull_card_data():

    card_information = {}
    sql_stmts = [
        'SELECT * FROM KittyWar_catcard;',
        'SELECT * FROM KittyWar_basiccards;',
        'SELECT * FROM KittyWar_chancecards;',
        'SELECT * FROM KittyWar_abilitycards;'
    ]

    card_information['cats'] = Network.sql_query(sql_stmts[0])
    # print(card_information['cats'])

    card_information['moves'] = Network.sql_query(sql_stmts[1])
    # print(card_information['moves'])

    card_information['chances'] = Network.sql_query(sql_stmts[2])
    # print(card_information['chances'])

    card_information['abilities'] = Network.sql_query(sql_stmts[3])
    # print(card_information['abilities'])

    return card_information


def update_display(root_display):

    root = root_display[0]
    server_display = root_display[1]

    log_count = Logger.log_count()
    for i in range(0, log_count):

        server_display.config(state=tkinter.NORMAL)
        server_display.insert(tkinter.END, "{}\n".format(Logger.retrieve()))
        server_display.pack()
        server_display.config(state=tkinter.DISABLED)

    root.after(100, update_display, (root, server_display))


def poll_connections(server):

    Logger.log("Server started")
    Logger.log(server.getsockname())
    connections = []

    while server_running:

        # Occasionally timeout from polling to check if the server is still running
        try:
            client, client_address = server.accept()
        except sock.timeout:
            continue

        Logger.log("Anonymous user connected from address: " + client_address[0])
        new_session = Session((client, client_address))
        new_session.start()

        connections.append(new_session)

    for connection in connections:
        if connection.is_alive():
            connection.kill()

    server.shutdown(sock.SHUT_RDWR)
    server.close()
    Logger.log("Server stopped")


def match_maker(match_event, lobby):

    while True:

        # Wait until someone queues for a match
        match_event.wait()

        # Check if an opponent is available
        if lobby.qsize() >= 2:

            # Grab two ready clients and pass them to a match process
            session1 = lobby.get()
            session2 = lobby.get()

            create_match(session1, session2)


def create_match(session1, session2):

    p1_name = session1.userprofile['username']
    p1_connection = session1.client
    p1_cats = session1.userprofile['records']['cats']
    player1 = Player(p1_name, p1_connection, p1_cats)

    p2_name = session2.userprofile['username']
    p2_connection = session2.client
    p2_cats = session2.userprofile['records']['cats']
    player2 = Player(p2_name, p2_connection, p2_cats)

    Logger.log("Creating match for " + p1_name +
               " & " + p2_name)

    match = Match()
    match.player1 = player1
    match.player2 = player2

    session1.match = match
    session2.match = match


def shutdown_server():

    Logger.log("Server stopping")
    global server_running
    server_running = False


if __name__ == "__main__":
    main()
