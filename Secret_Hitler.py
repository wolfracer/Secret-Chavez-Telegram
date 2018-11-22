# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import random
import pickle
import time
from enum import Enum
from telegram.error import Unauthorized, TelegramError

# Fix for #14
import sys, unicodedata, re
all_unicode_chars = (unichr(i) for i in xrange(sys.maxunicode))
non_printable_chars = ''.join(c for c in all_chars if unicodedata.category(c) == 'Cc')
non_printable_regex = re.compile('[%s]' % re.escape(control_chars))
def strip_non_printable(s):
    return control_char_re.sub('', s)
# /Fix for #14

markdown_regex = re.compile(".*((\[.*\]\(.*\))|\*|_|`).*")

BOT_USERNAME = "SuperSecretHitlerBot"
BLAME_RATELIMIT = 69 # seconds
TESTING = (__name__ == "__main__") # test whenever this file is run directly
# set TESTING to True to simulate a game locally
if not TESTING:
    import telegram_integration
    telegram_errors = [ ]

    # unnecessary in TESTING mode

EVERYONE_HITLER = False
EVERYONE_HITLER_EXPLANATION = "Hi, the game admins set the EVERYONE_HITLER flag, so you are not the only Hitler, so the game will keep going."

class Player(object):
    """
    Class for keeping track of an individual Secret Hitler player.
    """

    def __init__(self, _id, _name):
        """
        Set player's name and Telegram ID
        """
        self.id = _id
        self.name = _name
        self.game = None
        self.role = None
    def __str__(self):
        return self.name

    def send_message(self, msg, supress_errors=True):
        if TESTING:
            print "[ Message for {} ]\n{}".format(self, msg)
        else:
            try:
                telegram_integration.bot.send_message(chat_id=self.id, text=msg)
            except TelegramError as e:
                if supress_errors:
                    telegram_errors.append(e)
                    # network issues can cause errors in Telegram
                else:
                    raise e
    def get_markdown_tag(self):
        return "[{}](tg://user?id={})".format(self.name, self.id)

    def set_role(self, _role):
        """
        Sets a user's role/party affiliation and notifies them about it.
        """
        self.role = _role
        self.party = _role.replace("Hitler", "Fascist")
        self.send_message("Your secret role is {}".format(self.role))

    def join_game(self, _game):
        if self.leave_game(confirmed=False):
            self.game = _game
            return True
        else:
            return False # user must first deal with leaving their current game

    def leave_game(self, confirmed=False):
        if self.game is None:
            return True # nothing to leave
        elif confirmed:
            # TODO after testing, don't require confirmation to leave these games
            # or self.game.game_state in (GameStates.GAME_OVER, GameStates.ACCEPT_PLAYERS):
            self.game.remove_player(self)

            self.game = None
            self.role = None

            return True
        else:
            return False # must confirm to successfully leave a game in one
                         # of the more significant states

class GameStates(Enum):
    ACCEPT_PLAYERS = 1
    CHANCY_NOMINATION = 2
    ELECTION = 3
    LEG_PRES = 4
    LEG_CHANCY = 5
    VETO_CHOICE = 6
    INVESTIGATION = 7
    SPECIAL_ELECTION = 8
    EXECUTION = 9
    GAME_OVER = 10
class GameOverException(Exception):
    pass

class Game(object):
    def __init__(self, chat_id):
        """
        Initialize a game with a given chat location. Prepare deck/discard, begin accepting players.
        """
        if TESTING:
            self.deck = ['F', 'F', 'L', 'F', 'F', 'L', 'F', 'F', 'L', 'F', 'F', 'L', 'F', 'F', 'L', 'F', 'L']
        else:
            self.deck = ['L', 'L', 'L', 'L', 'L', 'L',
                        'F', 'F', 'F', 'F', 'F', 'F', 'F', 'F', 'F', 'F', 'F']
            random.shuffle(self.deck)

        self.global_chat = chat_id

        self.discard = []

        self.players = []
        self.president = None
        self.chancellor = None
        self.termlimited_players = set()
        self.dead_players = set()
        self.confirmed_not_hitlers = set()

        self.spectators = set()
        self.public_history = ""
        self.spectator_history = ""

        self.last_nonspecial_president = None
        self.vetoable_polcy = None
        self.president_veto_vote = None
        self.chancellor_veto_vote = None

        self.num_players = 0

        self.votes = []
        self.liberal = 0
        self.fascist = 0
        self.anarchy_progress = 0

        self.game_state = GameStates.ACCEPT_PLAYERS

    def reset_blame_ratelimit(self):
        self.last_blame = time.time() - BLAME_RATELIMIT

    def show(self, things_to_show = ["liberal","fascist","","anarchy","","players","","deck_stats","","hitler_warning"]):
        """
        Builds a textual representation of selected board stats,
        including:
        - Victory tracks
            - liberal                           "liberal"
            - fascist                           "fascist"
        - Anarchy tracker                       "anarchy"
        - Player order                          "players"
        - Draw/Discard pile information         "deck_stats"
            - detailed info on policies         "deck_stats_detailed"
        - HitlerZone information                "hitler_warning"
        - A blank line                          ""
        """
        message = ""
        to_show, rest = things_to_show[0], things_to_show[1:]
        if to_show == "liberal":
            message = "— Liberal Track —\n" + " ".join(["✖️","✖️","✖️","✖️","✖️"][:self.liberal]+["◻️","◻️","◻️","◻️","🕊"][self.liberal-5:])
        elif to_show == "fascist":
            fascist_track = ["◻️","◻️","🔮","🗡","🗡","☠️"]
            if self.num_players > 6:
                fascist_track[2] = "👔"
                fascist_track[1] = "🔎"
            if self.num_players > 8:
                fascist_track[0] = "🔎"
            message = "— Fascist Track —\n" + " ".join(["✖️","✖️","✖️","✖️","✖️","✖️"][:self.fascist]+fascist_track[self.fascist-6:])
        elif to_show == "anarchy":
            message = "— Anarchy Track —\n" + " ".join(["✖️","✖️","✖️"][:self.anarchy_progress]+["◻️","◻️","◻️"][:3-self.anarchy_progress])
        elif to_show == "players":
            message = "— Presidential Order —\n" + " ➡️ ".join([player.name for player in self.players if player not in self.dead_players]) + " 🔁"
        elif to_show == "deck_stats":
            message = "There are {} policies left in the draw pile, {} in the discard pile.".format(len(self.deck), len(self.discard))
        elif to_show == "deck_stats_detailed":
            message = "There are {} liberal and {} fascist policies in both piles combined.".format(6 - self.liberal, 11 - self.fascist)
        elif to_show == "hitler_warning":
            if self.fascist >= 3:
                message += "‼️ Beware: If Hitler gets elected as Chancellor, the fascists win the game! ‼️"
        elif to_show == "":
            message += "\n"
        elif len(to_show) > 0:
            message += "(I don’t know what you mean by “{}”)".format(to_show)
        if len(rest)>0:
            message += "\n" + self.show(rest)
        return message

    def start_game(self):
        """
        Starts a game:
        - assign all players roles
        - send fascists night-phase information
        - begin presidential rotation with the first presidnet nominating their chancellor
        """

        random.shuffle(self.players) # randomize seating order
        self.global_message("Randomized seating order:\n" + self.list_players())

        self.num_players = len(self.players)
        self.num_alive_players = self.num_players
        self.num_dead_players = 0
        self.reset_blame_ratelimit()

        if TESTING:
            roles = ["Liberal", "Fascist", "Liberal", "Hitler", "Liberal", "Liberal", "Fascist", "Liberal", "Fascist", "Liberal"]
            for i in range(len(self.players)):
                self.players[i].set_role(roles[i])
                # NOTE: testing configuration does not "notify" fascists of night-phase info (if this breaks, it'll be apparent pretty quickly)
        else:
            if EVERYONE_HITLER and self.num_players >= 7:
                for p in self.players:
                    p.set_role("Hitler")
            else:
                if self.num_players == 5 or self.num_players == 6: # 1F + H
                    fascists = random.sample(self.players, 2)
                elif self.num_players == 7 or self.num_players == 8: # 2F + H
                    fascists = random.sample(self.players, 3)
                elif self.num_players == 9 or self.num_players == 10: # 3F + H
                    fascists = random.sample(self.players, 4)
                else:
                    raise Exception("Invalid number of players")

                for p in self.players:
                    if p == fascists[0]:
                        p.set_role("Hitler")
                        if self.num_players <= 6:
                            p.send_message("Fascist: {}".format(fascists[1]))
                    elif p in fascists:
                        p.set_role("Fascist")
                        if self.num_players <= 6:
                            p.send_message("Hitler: {}".format(fascists[0]))
                        else:
                            p.send_message("Other Fascist{}: {}\nHitler: {}".format("s" if len(fascists) > 3 else "", ", ".join([ other_p.name for other_p in fascists[1:] if other_p != p ]), fascists[0]))
                    else:
                        p.set_role("Liberal")

        self.record_data("ROLES:\n" + "\n".join(["{} - {}".format(p, p.role) for p in self.players]) + "\n\n", spectator_only=True)

        self.president = self.players[0]
        self.set_game_state(GameStates.CHANCY_NOMINATION)

    def global_message(self, msg, supress_errors=True):
        """
        Send a message to all players using the chat specified in the constructor.
        """
        if TESTING:
            print "[ Message for everyone ]\n{}".format(msg)
        else:
            try:
                telegram_integration.bot.send_message(chat_id=self.global_chat, text=msg)
            except TelegramError as e:
                if supress_errors:
                    telegram_errors.append(e)
                    # network issues can cause errors in Telegram
                else:
                    raise e

    def record_data(self, msg, spectator_only=False):
        self.spectator_history += msg
        if spectator_only:
            for p in self.spectators:
                p.send_message(msg)
        else:
            self.public_history += msg
    def add_spectator(self, target):
        if target not in self.spectators:
            self.spectators.add(target)
            target.send_message(self.spectator_history)
    def remove_spectator(self, target):
        if target in self.spectators:
            self.spectators.remove(target)

    @staticmethod
    def str_to_policy(vote_str):
        """
        Helper function for interpreting a policy by the strings a user could have entered.
        Returns "F", "L", or None (if the policy could not be determined)
        """
        vote_str = vote_str.lower()
        if vote_str in ("f", "fascist", "r", "red") or vote_str.replace(" ","").find("spicy") != -1:
            return "F"
        elif vote_str in ("l", "liberal", "b", "blue") or vote_str.replace(" ","").find("nice") != -1:
            return "L"
        else:
            return None
    def get_player(self, player_str):
        """
        Helper function for getting a player from their index or name (which they could be referred to by).
        Returns None if player could not be identified.
        """
        if player_str.isdigit() and int(player_str) > 0 and int(player_str) <= self.num_players:
            return self.players[int(player_str) - 1]
        else:
            for p in self.players:
                if p.name.lower() == player_str.lower(): #p.name.find(player_str) != -1:
                    return p
            return None

    def check_name(self, name, current_player=None):
        """
        Check if a name is valid. If it is valid, return None, otherwise,
        return an appropriate error message about why the name is not valid.
        """
        name = strip_non_printable(name) # Fix for #14
        for forbidden_name in ("hitler", "me too thanks"):
            if name.lower() == forbidden_name:
                return "Error: {} is not a valid name because it is too similar to {}".format(name, forbidden_name)

        if name.isdigit() and int(name) <= 10:
            return "Error: name cannot be a number between 1 and 10"

        if name.endswith("(TL)") or name.endswith("(P)") or name.endswith("(C)") \
            or name.endswith("(RIP)") or name.endswith("(CNH)"):
            return "Error: names cannot spoof the annotations from /listplayers"
        if markdown_regex.match(name):
            return "Error: names cannot contain markdown characters"
        for p in self.players:
            if p != current_player and p.name.lower() == name.lower():
                return "Error: name '{}' is already taken".format(name)

        return None

    def list_players(self):
        """
        List all players (separated by newlines) with their indices and annotations:
        (P) indicates a president/presidential candidate
        (C) indicates a chancellor/chancellor candidate
        (TL) indicates a term-limited player
        (RIP) indicates a dead player
        (CNH) indicates a player that has been proven not to be Hitler
        """
        ret = ""
        for i in range(len(self.players)):
            status = ""
            if self.players[i] == self.president:
                status += " (P)"
            if self.players[i] == self.chancellor:
                status += " (C)"
            if self.players[i] in self.termlimited_players:
                status += " (TL)"
            if self.players[i] in self.dead_players:
                status += " (RIP)"
            if self.players[i] in self.confirmed_not_hitlers:
                status += " (CNH)"
            ret += "({}) {}{}\n".format(i + 1, self.players[i], status)

        return ret
    def add_player(self, p):
        """
        Given a Player p, add them to the game.
        """
        self.players.append(p)
        self.votes.append(None)
        self.num_players += 1

    def remove_player(self, p):
        """
        Remove a Player p from the game. (If p is not in the game, does nothing)
        Only valid before game starts or, theoretically, if they're dead (untested)
        If this method is called on a live player after the game has begun, the game will self-destruct
        (reveal all player roles and declare game over).
        """
        if p not in self.players:
            return # alredy "removed" because not in
        elif self.game_state == GameStates.ACCEPT_PLAYERS:
            self.players.remove(p)
            self.votes.pop()
            self.num_players -= 1
        elif p in self.dead_players: # TODO probably unnecessary
            index = self.players.index(p)
            self.players.pop(index)
            self.votes.pop(index)
            self.num_players -= 1
            self.num_dead_players -= 1
        else:
            self.global_message("Player {} left, so this game is self-destructing".format(p))
            self.set_game_state(GameStates.GAME_OVER)
            return
        leave_message = "Player {} has left".format(p)
        # If we're staging a new game, show updated staging info
        if self.game_state == GameStates.ACCEPT_PLAYERS:
            if self.num_players < 5:
                leave_message += "\nYou need {} more players before you can start.".format(["5️⃣","4️⃣","3️⃣","2️⃣","1️⃣"][self.num_players],"" if self.num_players==4 else "s")
            else:
                leave_message += "\nType /startgame to start the game with {} players!".format(self.num_players)
        self.global_message(leave_message)

    def select_chancellor(self, target):
        """
        Assumes state is CHANCY_NOMINATION and target in self.players.
        Select player `target` for chancellor.
        """
        if target in self.termlimited_players or target in self.dead_players or target == self.president:
            return False
        else:
            self.chancellor = target

            self.global_message("President {} has nominated Chancellor {}.".format(self.president, self.chancellor))
            #self.global_message("Now voting on {}/{}".format(self.president, self.chancellor))
            self.set_game_state(GameStates.ELECTION)
            self.record_data("{}/{} ".format(self.president, self.chancellor), spectator_only=False)

            return True

    def cast_vote(self, player, vote):
        """
        Assumes current state is ELECTION.
        Casts a vote for a player.
        """
        self.players[self.players.index(player)] = vote
    def list_nonvoters(self):
        """
        Assumes current state is ELECTION.
        List (and tags) all players who have not voted, separated by newlines.
        """
        return "\n".join([ self.players[i].get_markdown_tag() for i in range(self.num_players) if self.votes[i] is None and self.players[i] not in self.dead_players ])
    def election_is_done(self):
        """
        Assumes current state is ELECTION.
        Determine whether an election is done (all alive players have voted)
        """
        return self.votes.count(None) == self.num_dead_players
    def election_call(self):
        """
        Assumes current state is ELECTION.
        Gets the result of an election:
         - True if passed
         - False if failed
         - None if result cannot yet be determined
        """
        if self.votes.count(True) > self.num_alive_players / 2:
            return True
        elif self.votes.count(False) >= self.num_alive_players / 2:
            return False
        else:
            return None
    def election_results(self):
        """
        Assumes current state is ELECTION.
        Get election results in user-friendy format (list of "player - vote" strings, separated by newlines)
        """
        return "\n".join([ "{} - {}".format(self.players[i], "ja" if self.votes[i] else "nein") for i in range(self.num_players) if self.players[i] not in self.dead_players])
    def update_termlimits(self):
        """
        Updates term-limits:
        replaces current TLs with current president/chancellor, or just chancellor if there are <= 5 players remaining

        Assumes neither self.president nor self.chancellor is None
        """
        self.termlimited_players.clear()
        self.termlimited_players.add(self.chancellor)
        if self.num_players - len(self.dead_players) > 5:
            self.termlimited_players.add(self.president)

    def end_election(self):
        """
        Perform actions required at end of an election:
         - broadcast voting record
         - determine and announce result
         - if election passed:
           - check if Hitler was elected chancellor with >=3F and end game if so
           - update term-limits
           - reset Election Tracker
           - begin Legislative Session
         - if election failed
           - increment election counter, checking for anarchy
           - move presidential nomination to next player
        """
        # assert self.election_is_done()
        election_result = self.election_call()

        self.global_message("JA!" if election_result else "NEIN!")
        self.global_message(self.election_results())

        vote_bits = "".join([{True: "1", False: "0", None: "-"}[vote] for vote in self.votes])
        self.record_data("({}) - \n".format(vote_bits), spectator_only=False)

        if election_result:
            if self.fascist >= 3:
                if self.chancellor.role == "Hitler":
                    if EVERYONE_HITLER:
                        self.chancellor.send_message(EVERYONE_HITLER_EXPLANATION)
                    else:
                        self.end_game("Fascist", "Hitler was elected chancellor")
                else:
                    self.confirmed_not_hitlers.add(self.chancellor)

            self.set_game_state(GameStates.LEG_PRES)

            self.update_termlimits()
            self.anarchy_progress = 0
        else:
            self.record_data("NEIN\n", spectator_only=False)

            self.anarchy_progress += 1
            if self.anarchy_progress == 3:
                self.anarchy()

            self.advance_presidency()

        self.votes = [None] * self.num_players

    def president_legislate(self, discard):
        """
        Performs the president's legislative action: discards the given policy
        from the top 3. Returns True if successful (input was valid and in top 3)
        and False if input was invalid.
        """
        if discard in self.deck[:3]:
            self.deck.remove(discard)
            self.discard.append(discard)

            self.set_game_state(GameStates.LEG_CHANCY)
            return True
        else:
            return False
    def chancellor_legislate(self, enact):
        """
        Performs the chancellor's legislative action: enacts the given policy
        from the top 2. Returns True if successful (input was valid and in top 3)
        and False if input was invalid.
        """
        if enact in self.deck[:2]:
            self.deck.remove(enact)
            self.discard.append(self.deck.pop(0))

            if self.fascist == 5:
                self.vetoable_polcy = enact
                self.set_game_state(GameStates.VETO_CHOICE)
            else:
                self.pass_policy(enact)
            return True
        else:
            return False
    def check_reshuffle(self):
        """
        Check if the deck needs to be reshuffled (has <= 3 policies remaining).
        If it does, reshuffles the deck and announces this.
        """
        if len(self.deck) <= 3: # NOTE: official rules say not to shuffle when there are 3 policies but this is a house rule
            self.deck.extend(self.discard)
            del self.discard[:]

            random.shuffle(self.deck)

            self.global_message("Deck has been reshuffled.")
            self.record_data("*deck reshuffled*\n", spectator_only=False)

    def check_veto(self):
        """
        When veto power is enabled, checks if a veto should occur.
         - If the result is still undeterminable, does nothing
         - If both have agreed to the veto, performs the veto:
           * Announces that a veto has occurred
           * discards the policy that would have been enacted
           * Increments Election Tracker
         - If either declines to veto:
           * Announces who (first) blocked the veto
           * Passes the chosen policy
        """
        if False in (self.president_veto_vote, self.chancellor_veto_vote): # no veto
            if self.president_veto_vote is False:
                non_vetoer = "President " + str(self.president)
            else:
                non_vetoer = "Chancellor " + str(self.chancellor)

            self.global_message("{} has refused to veto".format(non_vetoer))
            self.pass_policy(self.vetoable_polcy)
            self.vetoable_polcy = None
            self.advance_presidency() # TODO: test presidential succession when veto occurrs
        elif self.president_veto_vote and self.chancellor_veto_vote: # veto
            self.global_message("VETO!")
            self.record_data(" - veto!\n", spectator_only=False)

            self.discard.append(self.vetoable_polcy)
            self.check_reshuffle()
            self.vetoable_polcy = None

            self.anarchy_progress = 1
            self.advance_presidency()
            # counter must be at 0 because an election must have just succeeded

    def pass_policy(self, policy, on_anarchy=False):
        """
        Passes 'policy' (assumes it is either "F" or "L") by calling the appropriate function.
        It then checks the deck's shuffle necessity and,
        if we don't need to wait for a decision related to executive power (according to the game_state),
        advances the presidency
        """
        if policy == "L":
            self.pass_liberal()
        else:
            self.pass_fascist(on_anarchy)

        self.record_data(policy + "\n", spectator_only=False)

        self.check_reshuffle()
        if not on_anarchy and self.game_state == GameStates.LEG_CHANCY: # don't need to wait for other decisison
            self.advance_presidency()

        self.global_message(self.show())

    def pass_liberal(self):
        """
        Pass a liberal policy, announce this fact, and check if this creates a liberal victory
        """
        self.liberal += 1
        self.global_message("A liberal policy was passed!")

        if self.liberal == 5:
            self.end_game("Liberal", "5 Liberal policies were enacted")
    def pass_fascist(self, on_anarchy):
        """
        Pass a fascist policy, announce this fact, check if this creates a fascist victory
        If not on anarcy, initiates appropriate executive powers depending on policy number and player count
        """
        self.fascist += 1
        if self.fascist == 3:
            self.global_message("A fascist policy was passed! Welcome to the HitlerZone™!")
        else:
            self.global_message("A fascist policy was passed!")

        if self.fascist == 6:
            self.end_game("Fascist", "6 Fascist policies were enacted")

        if on_anarchy:
            return # any executive powers ignored in anarchy

        if self.fascist == 1 and self.num_players in (9, 10):
            self.set_game_state(GameStates.INVESTIGATION)
        elif self.fascist == 2 and self.num_players in (7, 8, 9, 10):
                self.set_game_state(GameStates.INVESTIGATION)
        elif self.fascist == 3:
            if self.num_players in (5,6): # EXAMINE
                self.check_reshuffle()
                self.global_message("President ({}) is examining top 3 policies".format(self.president))
                self.president.send_message("Top three policies are: ")
                self.deck_peek(self.president, 3)
            elif self.num_players in (7, 8, 9, 10):
                self.set_game_state(GameStates.SPECIAL_ELECTION)
        elif self.fascist == 4 or self.fascist == 5:
            self.set_game_state(GameStates.EXECUTION)

    def next_alive_player(self, starting_after):
        """
        Presidential-succession helper function: determines the next (alive)
        player in the normal rotation after a given player.
        """
        target_index = self.players.index(starting_after)
        while self.players[target_index] == starting_after or self.players[target_index] in self.dead_players:
            target_index += 1
            target_index %= self.num_players
        return self.players[target_index]
    def advance_presidency(self):
        """
        Passes presidency to next player in the rotation or, if the previous election was a special election,
        resumes the normal rotation.
        """
        if self.last_nonspecial_president == None: # normal rotation
            self.president = self.next_alive_player(self.president)
        else: # returning from special election
            self.president = self.next_alive_player(self.last_nonspecial_president)
            self.last_nonspecial_president = None # indicate that special-election is over

        self.chancellor = None # new president must now nominate chancellor
        self.set_game_state(GameStates.CHANCY_NOMINATION)

    def investigate(self, origin, target):
        """
        Simulates an investigation:
         - Announces who is investigating whom
         - Sends player their target's party affiliation
        """
        origin.send_message("<{0}> party affiliation is <{0.party}>".format(target))
        self.global_message("{} has investigated {}".format(origin, target))
        self.record_data(" - investigates {}\n".format(target), spectator_only=False)
    def deck_peek(self, who, num=3):
        """
        Sends player `who` a message indicating the top `num` policy tiles.
        """
        policies = "".join(self.deck[:num])

        who.send_message(policies)

        spectator_who = {self.president: "President ({})", self.chancellor: "Chancellor ({})"}.get(who, "{}")
        spectator_who = spectator_who.format(who)

        self.record_data(" - {} peeks at {}\n".format(spectator_who, policies), spectator_only=True)
    def special_elect(self, target):
        """
        Simulate a special election:
         - Set someone as the next president
         - Save the current spot in the rotation to return to

        Returns True if successful and False if input was invalid (tried to nominate self)
        """
        if target == self.president:
            return False # cannot special elect self

        self.last_nonspecial_president = self.president
        self.president = target

        self.record_data(" - special elects {}\n".format(target), spectator_only=False)
        return True

    def kill(self, target):
        """
        Simulate killing a player `target`.
            If this player is Hitler, the game will end in a liberal victory
            Otherwise, this player will be unable to vote, be nominated, or run for president
            for the remainder of the game.
        """
        self.record_data(" - kills {}\n".format(target), spectator_only=False)
        if target.role == "Hitler":
            if EVERYONE_HITLER:
                target.send_message(EVERYONE_HITLER_EXPLANATION)
            else:
                self.end_game("Liberal", "Hitler was killed")
        else:
            self.dead_players.add(target)
            self.num_alive_players -= 1
            self.num_dead_players += 1

    def anarchy(self):
        """
        Simulate "anarchy"
         - pass the top policy
         - ignore any powers
         - reset election tracker
         - and clear term limits
        """
        self.check_reshuffle()
        self.record_data(" - anarchy!\n", spectator_only=False)
        self.pass_policy(self.deck.pop(0), on_anarchy=True)

        self.termlimited_players.clear()
        self.anarchy_progress = 0
        self.advance_presidency()

    def end_game(self, winning_party, reason):
        """
        End the game by announcing the victory, setting state to GameStates.GAME_OVER,
        and raising a GameOverException (must be caught and handled)
        """
        self.global_message("The {} team wins! ({}.)".format(winning_party, reason))
        self.set_game_state(GameStates.GAME_OVER)
        raise GameOverException("The {} team wins! ({}.)".format(winning_party, reason))

    def set_game_state(self, new_state, repeat=False):
        """
        Change the game state to new_state and perform any actions associated with that state's beginning:
        Announce the state change, notify relevant president/chancellor about what they must do.
        """

        if self.game_state == new_state and not repeat:
            return # don't repeat state change unless specifically requested

        self.game_state = new_state
        self.reset_blame_ratelimit()

        if self.game_state == GameStates.CHANCY_NOMINATION:
            self.global_message("President {} must nominate a chancellor".format(self.president))
            self.president.send_message("Pick your chancellor!\n(\"/nominate [player name or index]\")")
        elif self.game_state == GameStates.ELECTION:
            self.global_message("Election: Vote on President {} and Chancellor {}".format(self.president, self.chancellor))
            for p in self.players: # send individual messages to clarify who you're voting on
                if p not in self.dead_players:
                    p.send_message("{}/{} vote (\"/ja\" or \"/nein\"):".format(self.president, self.chancellor))
        elif self.game_state == GameStates.LEG_PRES:
            self.global_message("Legislative session in progress (waiting on President {})".format(self.president))
            self.president.send_message("Pick a policy to discard!\n(\"/discard [POLICY]\")")
            self.deck_peek(self.president, 3)
        elif self.game_state == GameStates.LEG_CHANCY:
            self.global_message("Legislative session in progress (waiting on Chancellor {})".format(self.chancellor))
            self.chancellor.send_message("Pick a policy to enact!\n(\"/enact [POLICY]\")")
            self.deck_peek(self.chancellor, 2)
        elif self.game_state == GameStates.VETO_CHOICE:
            self.global_message("President ({}) and Chancellor ({}) are deciding whether to veto (both must agree to do so)".format(self.president, self.chancellor))
            self.president.send_message("Would you like to veto? (\"/ja\" or \"/nein\")")
            self.chancellor.send_message("Would you like to veto? (\"/ja\" or \"/nein\")")
            self.president_veto_vote = None
            self.chancellor_veto_vote = None
        elif self.game_state == GameStates.INVESTIGATION:
            self.global_message("President ({}) must investigate another player".format(self.president))
            self.president.send_message("Pick a player to investigate!\n(\"/investigate [player name or index]\")" + self.list_players())
        elif self.game_state == GameStates.SPECIAL_ELECTION:
            self.global_message("Special Election: President ({}) must choose the next presidential candidate".format(self.president))
            self.president.send_message("Pick the next presidential candidate!\n(\"/nominate [player name or index]\")" + self.list_players())
        elif self.game_state == GameStates.EXECUTION:
            self.global_message("President ({}) must kill someone".format(self.president))
            self.president.send_message("Pick someone to kill!\n(\"/kill [player name or index]\")" + self.list_players())
        elif self.game_state == GameStates.GAME_OVER:
            # self.global_message("\n".join(["{} - {}".format(p, p.role) for p in self.players]))
            # reveal all player roles when the game has ended

            # reveal EVERYTHING THAT HAPPENED when game ends
            self.global_message(self.spectator_history)

            for p in self.players:
                p.game = None # allow players to join other games


    def save(self, fname):
        """
        Save all current game info to a file
        """

        with open(fname, "w") as out_file:
            pickle.dump(self, out_file)

    @classmethod
    def load(cls, fname):
        """
        Load a game from a file (output by save)
        """
        with open(fname, "r") as in_file:
            return pickle.load(in_file)

    def get_blocked_player(self, test_msg="Trying to start game!"):
        """
        This function attempts to send all registered players a message to
        ensure that direct messages work with them. If we find a player has not
        messaged the bot or has blocked it, the message will fail.  This
        function will return this player's Player object. If everybody was good
        (i.e. we're good to start the game), returns None.
        """

        for p in self.players:
            try:
                p.send_message(test_msg, supress_errors=False)
            except Unauthorized as e:
                return p
        return None

    ACCEPTED_COMMANDS = ("listplayers", "changename", "joingame", "startgame",
        "boardstats", "deckstats", "anarchystats", "blame", "ja", "nein",
        "nominate", "kill", "investigate", "enact", "discard", "whois",
        "spectate", "unspectate", "logs")
    def handle_message(self, from_player, command, args=""):
        """
        Handle the message "/command args" from from_player. Using the game state
        and origin, perform the appropriate actions and change state if necessary.
        Returns a string that the bot should send as a reply or None if no reply is necessary.
        """
        # commands valid at any time
        if command == "listplayers":
            return self.list_players()
        elif command == "whois":
            target = self.get_player(args)
            if target:
                return target.get_markdown_tag()
            else:
                return "Usage: /whois \[player name]"
        elif command == "changename":
            if from_player in self.players:
                if args == "":
                    return "Must specify new name like this: /changename [NEW NAME]"
                else:
                    new_name = args
                    error_msg = self.check_name(new_name, current_player=from_player)
                    if error_msg:
                        return error_msg
                    else:
                        from_player.name = new_name
                        return "Successfully changed name to '{}'".format(new_name)
            else:
                return "Must be in game to change nickname"
        elif command == "spectate":
            if from_player in self.players and from_player not in self.dead_players:
                return "Error: you cannot spectate a game you're in. Please /leave to spectate."
            elif from_player in self.spectators:
                return "Error: you are already spectating. /unspectate to stop."
            else:
                from_player.send_message("You are now spectating!")
                self.add_spectator(from_player)
                return
        elif command == "unspectate":
            self.remove_spectator(from_player)
            from_player.send_message("You are no longer spectating")
        elif command == "logs":
            return self.public_history
        elif self.game_state == GameStates.ACCEPT_PLAYERS:
            if command == "joingame":
                if self.num_players == 10:
                    return "Error: game is full"
                elif from_player in self.players:
                    return "Error: you've already joined"
                elif from_player in self.spectators:
                    return "Error: you cannot join a game you're spectating. Please /unspectate to join"
                elif not from_player.join_game(self):
                    return "Error: you've already joined another game! Leave/end that one to play here."
                self.add_player(from_player)
                welcome_message = "Welcome, {}! Make sure to [message me directly](t.me/{}) before the game starts so I can send you secret information.".format(from_player.name, BOT_USERNAME)
                # Show updated staging info
                if self.num_players < 5:
                    welcome_message += "\nYou need {} more players before you can start.".format(["5️⃣","4️⃣","3️⃣","2️⃣","1️⃣"][self.num_players],"" if self.num_players==4 else "s")
                else:
                    welcome_message += "\nType /startgame to start the game with {} players!".format(self.num_players)
                return welcome_message
            elif command == "startgame":
                if self.num_players < 5:
                    return "Error: only {} players".format(self.num_players)

                blocked = self.get_blocked_player()
                if blocked:
                    return "Error: All players must have messaged and not blocked @{}! {} must message/unblock me." \
                        .format(BOT_USERNAME, blocked.get_markdown_tag()) \
                        .replace("_","\\_") # some Markdown escaping may be necessary

                self.start_game()
                return
            else:
                return "Error: game has not started"
        if command == "boardstats":
            return self.show()
        elif command == "deckstats":
            return self.show(["deck_stats", "deck_stats_detailed"])
        elif command == "anarchystats":
            return self.show(["anarchy"])
        elif command == "blame":
            if time.time() - self.last_blame < BLAME_RATELIMIT:
                from_player.send_message("Hey, slow down!")
                return
                # avoid spam by respding with DM (good luck if there's Darbs playing)

            self.last_blame = time.time()
            pres_tag = "(president)"
            chancy_tag = "(chancellor)"
            if self.president is not None:
                pres_tag = self.president.get_markdown_tag()
            if self.chancellor is not None:
                chancy_tag = self.chancellor.get_markdown_tag()

            if self.game_state == GameStates.ELECTION:
                return "People who haven't yet voted:\n" + self.list_nonvoters()
            elif self.game_state == GameStates.CHANCY_NOMINATION:
                return "{} needs to nominate a chancellor!".format(pres_tag)
            elif self.game_state == GameStates.LEG_PRES:
                return "{} needs to discard a policy!".format(pres_tag)
            elif self.game_state == GameStates.LEG_CHANCY:
                return "{} needs to enact a policy!".format(chancy_tag)
            elif self.game_state == GameStates.VETO_CHOICE:
                return "{} and {} need to decide whether to veto!".format(pres_tag, chancy_tag)
            elif self.game_state == GameStates.INVESTIGATION:
                return "{} needs to pick someone to investigate!".format(pres_tag)
            elif self.game_state == GameStates.SPECIAL_ELECTION:
                return "{} needs to pick someone to special elect!".format(pres_tag)
            elif self.game_state == GameStates.EXECUTION:
                return "{} needs to pick someone to kill!".format(pres_tag)
        elif from_player not in self.players or from_player in self.dead_players:
            return "Error: Spectators/dead players cannot use commands that modify game data"
            # further commands affect game state
        elif command in ("nominate", "kill", "investigate") and from_player == self.president:
            # commands that involve the president selecting another player
            target = self.get_player(args)

            target_confirmed = False
            if self.game_state == GameStates.EXECUTION and command == "kill":
                if args.lower().find("me too thanks") != -1:
                    target = from_player
                    target_confirmed = True
                elif from_player.party == "Fascist" and args.lower().find("hitler") != -1:
                    for p in players:
                        if p.role == "Hitler":
                            target = p
                            target_confirmed = True
                            break

            if target == None:
                return "Error: Could not parse player."
            if command == "nominate":
                if self.game_state == GameStates.CHANCY_NOMINATION:
                    if self.select_chancellor(target):
                        return None # "You have nominated {} for chancellor.".format(target)
                    else:
                        return "Error: {} is term-limited/dead/yourself.".format(target)
                elif self.game_state == GameStates.SPECIAL_ELECTION:
                    if self.special_elect(target):
                        self.set_game_state(GameStates.CHANCY_NOMINATION)
                        return None # "You have nominated {} for president.".format(target)
                    else:
                        return "Error: you can't nominate yourself for president.".format(target)
            elif command == "kill" and self.game_state == GameStates.EXECUTION:
                if from_player == target and not target_confirmed:
                    return "You are about to kill yourself (technically allowed by the rules). Reply '/kill me too thanks' to confirm suicide."
                elif from_player.role == "Fascist" and target.role == "Hitler" and not target_confirmed:
                    from_player.send_message("It looks like you are trying to kill Hitler. You WILL LOSE THE GAME if you proceed. Reply '/kill hitler' to confirm.")
                    return
                else:
                    self.kill(target)
                    self.advance_presidency()
                    self.global_message("{} has killed {}.".format(from_player, target))
                    target.send_message("You are now dead. RIP. Remember " + \
                        "that dead players SHOULD NOT TALK, reveal their " + \
                        "secret role, or otherwise influence the game!" )
            elif command == "investigate" and self.game_state == GameStates.INVESTIGATION:
                self.investigate(from_player, target)
                self.advance_presidency()
        elif command in ("ja", "nein"):
            vote = (command == "ja")
            if self.game_state == GameStates.ELECTION:
                self.votes[self.players.index(from_player)] = vote

                if self.election_is_done():
                    self.end_election()
                    return None
                else:
                    if vote:
                        return "Ja vote recorded; quickly /nein to switch"
                    else:
                        return "Nein vote recorded; quickly /ja to switch"
            elif self.game_state == GameStates.VETO_CHOICE and from_player in (self.president, self.chancellor):
                if from_player == self.president:
                    self.president_veto_vote = vote
                elif from_player == self.chancellor:
                    self.chancellor_veto_vote = vote

                self.check_veto()
                return "Veto vote recorded"
        elif command in ("enact", "discard"):
            policy = Game.str_to_policy(args)
            if policy is None:
                return "Error: Policy could not be parsed"

            if command == "discard" and self.game_state == GameStates.LEG_PRES and from_player == self.president:
                if self.president_legislate(policy):
                    return "You have discarded {}".format(policy)
                else:
                    return "Error: Given policy not in top 3"
            elif self.game_state == GameStates.LEG_CHANCY and from_player == self.chancellor:
                if command == "discard" and self.deck[0] != self.deck[1]:
                    policy = "L" if policy == "F" else "F"

                if self.chancellor_legislate(policy):
                    return None
                    # if self.fascist < 5: # prevents "thanks" from happening after veto notification
                    #     return "Thanks!"
                else:
                    return "Error: Given policy not in top 2"
        else:
            return "/{} is not valid here".format(command)
    def TEST_handle(self, player, command, args=""):
        """
        TESTING FUNCTION: run self.handle_message(player, command, args) but print out
        the input and output for debugging
        """
        response = self.handle_message(player, command, args)
        print "[{}] {} {}".format(player, command, args)
        if response:
            print "[Reply to {}] {}".format(player, response)
    def TEST_vote(self, should_pass=True):
        """
        TESTING FUNCTION: use TEST_handle to simulate a unanimous "ja" (or unanimous "nein" if should_pass=False)
        This helps keep test-game code concise when you're not explicitly testing elections
        """
        for p in self.players:
            if p not in self.dead_players:
                self.TEST_handle(p, "ja" if should_pass else "nein")

def test_game():
    game = Game(None)
    players = [
        Player("1", "A"),
        Player("2", "B"),
        Player("3", "C"),
        Player("4", "D"),
        Player("5", "E"),
        Player("6", "F"),
        Player("7", "G") ]

    for p in players:
        game.add_player(p)

    game.TEST_handle(players[2], "startgame")

    game.TEST_handle(players[0], "nominate", "D") # election 1
    game.TEST_vote()

    game.TEST_handle(players[0], "discard", "L")
    game.TEST_handle(players[3], "enact", "F") # 0L / 1F

    game.TEST_handle(players[1], "nominate", "E") # election 2
    game.TEST_vote()
    game.TEST_handle(players[1], "discard", "L")
    game.TEST_handle(players[4], "enact", "F")

    game.TEST_handle(players[1], "investigate", "E")

    game.TEST_handle(players[2], "nominate", "F") # election 3
    game.TEST_vote()
    game.TEST_handle(players[2], "discard", "L")
    game.TEST_handle(players[5], "enact", "F")

    game.TEST_handle(players[2], "nominate", "B") # special elect

    game.TEST_handle(players[1], "nominate", "G") # election 4
    game.TEST_vote()
    game.TEST_handle(players[1], "discard", "L")
    game.TEST_handle(players[6], "enact", "F")

    game.TEST_handle(players[1], "kill", "me too thanks") # execution

    game.TEST_handle(players[3], "nominate", "A") # election 5 - should fail because dead people cannot vote and ties fail
    game.TEST_handle(players[0], "nein")
    game.TEST_handle(players[1], "ja") # players[1] is dead
    game.TEST_handle(players[2], "ja")
    game.TEST_handle(players[3], "nein")
    game.TEST_handle(players[4], "nein")
    game.TEST_handle(players[5], "ja")
    game.TEST_handle(players[6], "ja")

    game.TEST_handle(players[4], "nominate", "A") # election 6 - fail
    game.TEST_handle(players[0], "nein")
    game.TEST_handle(players[2], "ja")
    game.TEST_handle(players[3], "nein")
    game.TEST_handle(players[4], "nein")
    game.TEST_handle(players[5], "ja")
    game.TEST_handle(players[6], "ja")

    game.TEST_handle(players[5], "nominate", "A") # election 7 - fail
    game.TEST_handle(players[0], "nein")
    game.TEST_handle(players[2], "ja")
    game.TEST_handle(players[3], "nein")
    game.TEST_handle(players[4], "nein")
    game.TEST_handle(players[5], "ja")
    game.TEST_handle(players[6], "ja")

    # anarchy, second bullet should be ignored

    game.TEST_handle(players[6], "nominate", "A")
    game.TEST_vote()

    game.TEST_handle(players[6], "discard", "s p i c y b o i")
    game.TEST_handle(players[0], "enact", "liberal") # check other policy nomenclature

    game.TEST_handle(players[0], "ja") #veto decisison
    game.TEST_handle(players[6], "nein")

    game.TEST_handle(players[0], "nominate", "D")
    game.TEST_vote()

    game.TEST_handle(players[0], "discard", "l")
    game.TEST_handle(players[3], "enact", "f")

    #veto decisison
    game.TEST_handle(players[0], "nein")
    # Fascist victory
    # game.handle_message(players[6], "ja") # other veto vote shouldn't matter

if TESTING:
    test_game()
