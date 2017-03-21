import socket as sock

from network import Network, WNetwork, Flags
from threading import Thread
from time import sleep
from logger import Logger, LogCodes


class Session(Thread):

    # Variables used by all sessions that must be set for it to work
    server_running = True

    card_information = None
    lobby = None
    match_event = None

    def __init__(self, client_info):

        Thread.__init__(self)
        self.name = 'session'
        self.daemon = False

        self.network = Network
        self.recv_size = 28

        self.authenticated = False
        self.userprofile = {'username': 'Anonymous'}
        self.client = client_info[0]
        self.client_address = client_info[1]
        self.match = None

    # Session Thread loop - runs until server is being shutdown or client disconnects
    def run(self):

        Logger.log("New session started", LogCodes.Session)

        if Network.check_wconnection(self.client):

            self.network = WNetwork
            self.network.handshake(self.client)
            self.recv_size = 2

        while self.server_running:

            # Receive flag and incoming data size
            data = self.network.receive_data(self.client, self.recv_size)
            if data is None:
                break

            # Process clients request and check if successful
            request = self.network.parse_request(self.client, data)

            if request:
                self.process_request(request)

            else:

                Logger.log(self.userprofile['username'] +
                           " request could not be parsed, closing connection", LogCodes.Session)
                self.kill()

        # Start shutting down session thread
        # If the user has disconnected during a match they incur a loss
        if self.match:
            self.match.disconnect(self.userprofile['username'])

        self.logout()
        self.shutdown()
        self.client.close()

        Logger.log(self.userprofile['username'] + " disconnected", LogCodes.Session)
        Logger.log(
            "Session thread for " + self.userprofile['username'] + " ending", LogCodes.Session)

    def shutdown(self):

        try:
            self.client.shutdown(sock.SHUT_RDWR)
        except OSError:
            pass

    def kill(self):

        self.server_running = False
        self.shutdown()

    def process_request(self, request):

        flag = request.flag

        Logger.log("Request: " + str(flag) + " " + str(request.token) +
                   " " + str(request.size), LogCodes.Session)
        Logger.log("Body: " + str(request.body), LogCodes.Session)

        # Check if the flag is valid
        if Flags.valid_flag(flag):

            # Disregard identity checking for web app testing
            # Check user identity for sensitive operations
            # if flag > Flags.LOGOUT:
            #     if not self.verified(request):
            #        Logger.log(
            #        self.userprofile['username'] + " is not authorized to use flag " +
            #        str(flag) + ", closing this connection", LogCodes.Session)

            #        self.kill()
            #        return

            # Check if the flag pertains to the session
            if flag in request_map:
                request_map[flag](self, request)

            # Check if the flag pertains to a match
            elif self.match:

                self.match.lock.acquire()
                self.match.process_request(self.userprofile['username'], request)
                self.match.lock.release()

                # If problem with match end
                if not self.match.match_valid:
                    self.match = None

        else:

            Logger.log(
                "Server does not support flag " + str(flag)
                + ", closing connection", LogCodes.Session)
            self.kill()

    def verified(self, request):

        if self.authenticated:
            if request.token == self.userprofile['token']:
                return True

        return False

    # Verifies user has actually logged through token authentication
    def login(self, request):

        # Prepare client response
        response = self.network.generate_responseh(request.flag, Flags.ONE_BYTE)

        # Retrieve username from request body
        username = request.body

        # If the user does not send username or connection error close connection
        if username is None:
            self.shutdown()

        # Log the username
        Logger.log("Body: " + username, LogCodes.Session)
        self.userprofile['username'] = username

        sql_stmts = [
            'SELECT id FROM auth_user WHERE username=\'{}\';',
            'SELECT token FROM KittyWar_userprofile WHERE user_id=\'{}\';'
        ]

        # Retrieve user id tied to username
        result = self.network.sql_query(sql_stmts[0].format(username))
        if result:

            user_id = result[0]['id']
            # With user id query users login token
            result = self.network.sql_query(sql_stmts[1].format(user_id))

            if result and request.token == result[0]['token']:

                self.userprofile['userid'] = user_id
                self.userprofile['token'] = result[0]['token']
                self.authenticated = True

                Logger.log(username + " authenticated", LogCodes.Session)
                response.append(Flags.SUCCESS)

            else:
                Logger.log(username + " failed authentication", LogCodes.Session)
                response.append(Flags.FAILURE)

        else:
            # Username is verified through django server so force close connection
            Logger.log(
                "No username/id found for " + username + ", force closing connection", LogCodes.Session)
            self.shutdown()

        self.network.send_data(self.userprofile['username'], self.client, response)

    # Logs user in for profile records - only pertains to web app
    def web_login(self, request):

        user_id = -1
        if request.body:
            user_id = int(request.body)

        self.userprofile['userid'] = user_id

    # Logs the user out by deleting their token and ending the session
    def logout(self, request=None):

        if self.authenticated:

            Logger.log(self.userprofile['username'] + " is logging out", LogCodes.Session)

            sql_stmt = "UPDATE KittyWar_userprofile SET token='' WHERE user_id=\'{}\';"
            self.network.sql_query(sql_stmt.format(self.userprofile['userid']))
            self.authenticated = False

            Logger.log(self.userprofile['username'] + " has logged out", LogCodes.Session)

        self.shutdown()

    def _user_profile(self):

        sql_stmts = [
            'SELECT draw,loss,wins,matches FROM KittyWar_userprofile WHERE user_id=\'{}\';',
            'SELECT catcard_id FROM KittyWar_userprofile_cats WHERE userprofile_id=\'{}\';'
        ]

        sql_stmt = sql_stmts[0].format(self.userprofile['userid'])
        records = self.network.sql_query(sql_stmt)
        sql_stmt = sql_stmts[1].format(self.userprofile['userid'])
        cats = self.network.sql_query(sql_stmt)

        records = records[0]
        records['cats'] = []

        for cat in cats:
            records['cats'].append(cat['catcard_id'])

        self.userprofile['records'] = records

    # Grab user profile information from database
    # then save it and send it back to the client
    def user_profile(self, request):

        self._user_profile()

        body = str(self.userprofile['records'])
        response = self.network.generate_responseb(request.flag, len(body), body)
        self.network.send_data(self.userprofile['username'], self.client, response)

    # Sends all card data to the client
    def all_cards(self, request):

        body = str(self.card_information)
        response = self.network.generate_responseb(request.flag, len(body), body)
        self.network.send_data(self.userprofile['username'], self.client, response)

    # Sends all cat card data to the client
    def cat_cards(self, request):

        body = str(self.card_information['cats'])
        response = self.network.generate_responseb(request.flag, len(body), body)
        self.network.send_data(self.userprofile['username'], self.client, response)

    # Sends all moveset card data to the client
    def basic_cards(self, request):

        body = str(self.card_information['moves'])
        response = self.network.generate_responseb(request.flag, len(body), body)
        self.network.send_data(self.userprofile['username'], self.client, response)

    # Sends all chance card data to the client
    def chance_cards(self, request):

        body = str(self.card_information['chances'])
        response = self.network.generate_responseb(request.flag, len(body), body)
        self.network.send_data(self.userprofile['username'], self.client, response)

    # Sends all ability card data to the client
    def ability_cards(self, request):

        body = str(self.card_information['abilities'])
        response = self.network.generate_responseb(request.flag, len(body), body)
        self.network.send_data(self.userprofile['username'], self.client, response)

    # Finds a match and records match results once match is finished
    def find_match(self, request):

        # Before finding a match ensure the user has their profile loaded
        if 'records' not in self.userprofile:
            self._user_profile()

        Logger.log(self.userprofile['username'] + " is finding a match", LogCodes.Match)
        self.lobby.put(self)

        # Periodically notify matchmaker and wait until match is found
        while self.match is None:

            self.match_event.set()
            self.match_event.clear()
            sleep(1)

        Logger.log("Match starting for " + self.userprofile['username'], LogCodes.Match)

        # At this point a match has been found so notify client
        response = self.network.generate_responseb(request.flag, Flags.ONE_BYTE, Flags.SUCCESS)
        self.network.send_data(self.userprofile['username'], self.client, response)

request_map = {

    Flags.LOGIN:         Session.login,
    Flags.WEB_LOGIN:     Session.web_login,
    Flags.LOGOUT:        Session.logout,
    Flags.FIND_MATCH:    Session.find_match,
    Flags.USER_PROFILE:  Session.user_profile,
    Flags.ALL_CARDS:     Session.all_cards,
    Flags.CAT_CARDS:     Session.cat_cards,
    Flags.BASIC_CARDS:   Session.basic_cards,
    Flags.CHANCE_CARDS:  Session.chance_cards,
    Flags.ABILITY_CARDS: Session.ability_cards
}
