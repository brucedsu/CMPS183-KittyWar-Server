#!/usr/bin/python3
# Kitty War game server
# TCP Port 2056

import socket as sock
import threading
import tkinter
import tkinter.scrolledtext
import tkinter.ttk as ttk

from network import Network
from sessions import Session
from match import Match, Player
from queue import Queue
from logger import Logger

server_port = 2056
server_running = True


def main():

    # Server networking setup
    # ##################################################################################################################

    # Create server
    server = sock.socket(sock.AF_INET, sock.SOCK_STREAM)
    server_address = ('localhost', server_port)

    # Prepare lobby and match making thread
    match_event = threading.Event()
    lobby = Queue()

    # Start match making thread
    matchmaker_thread = threading.Thread(target=match_maker, args=(match_event, lobby))
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
    polling_thread = threading.Thread(target=poll_connections, args=(server,))
    polling_thread.daemon = True
    polling_thread.start()

    # Server GUI code
    # ##################################################################################################################
    root = tkinter.Tk()
    root.geometry("600x600")
    root.title("KittyWar Game Server")

    notebook = ttk.Notebook(root)

    network_tab = ttk.Frame(notebook)
    session_tab = ttk.Frame(notebook)
    match_tab = ttk.Frame(notebook)
    ability_tab = ttk.Frame(notebook)
    chance_tab = ttk.Frame(notebook)

    # Add tabs to the notebook and pack it
    notebook.add(network_tab, text="Network")
    notebook.add(session_tab, text="Session")
    notebook.add(match_tab, text="Match")
    notebook.add(ability_tab, text="Ability")
    notebook.add(chance_tab, text="Chance")
    notebook.pack()

    # Create and packet text displays
    windows = [
        tkinter.scrolledtext.ScrolledText(network_tab),
        tkinter.scrolledtext.ScrolledText(session_tab),
        tkinter.scrolledtext.ScrolledText(match_tab),
        tkinter.scrolledtext.ScrolledText(ability_tab),
        tkinter.scrolledtext.ScrolledText(chance_tab)]

    for window in windows:

        window.config(state=tkinter.DISABLED)
        window.pack()

    # Create shutdown button
    shutdown_button = tkinter.Button(root, text="Shutdown Server", command=shutdown_server)
    shutdown_button.pack()

    # Start GUI and set update to every 250ms
    root.after(Logger.log_interval, update_display, (root, windows))
    root.mainloop()


# Updates the server GUI based on log interval
def update_display(root_pkg):

    root = root_pkg[0]
    windows = root_pkg[1]

    window_index = 0
    for window in windows:

        log_count = Logger.log_count(window_index)
        for log_index in range(0, log_count):

            window.config(state=tkinter.NORMAL)
            window.insert(tkinter.END, "{}\n".format(Logger.retrieve(window_index)))
            window.pack()
            window.config(state=tkinter.DISABLED)

        window_index += 1

    root.after(Logger.log_interval, update_display, (root, windows))


# Grab latest card data from the database
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


def poll_connections(server):

    Logger.log("Server started")
    Logger.log(server.getsockname())

    while server_running:

        # Occasionally timeout from polling to check if the server is still running
        try:
            client, client_address = server.accept()
        except sock.timeout:
            continue

        Logger.log("Anonymous user connected from address: " + client_address[0])
        new_session = Session((client, client_address))
        new_session.start()

    Logger.log("Closing all sessions")
    for live_thread in threading.enumerate():
        if live_thread.name == 'session':
            live_thread.kill()

    active_count = threading.active_count()
    while active_count >= 4:

        update_count = threading.active_count()
        if active_count > update_count:

            active_count = update_count
            Logger.log("Sessions remaining: " + str(active_count - 3))

    Logger.log("*Safe to close server application*")

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

    global server_running
    if server_running:

        Logger.log("Server stopping")
        server_running = False

    else:
        Logger.log("Server already stopped")

if __name__ == "__main__":
    main()
