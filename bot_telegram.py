#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import os
import sys

import telegram
from telegram.error import TelegramError
from telegram.ext import Updater, CommandHandler

import secret_hitler

with open("config/key", "r") as file:
    API_KEY = file.read().rstrip()

bot = telegram.Bot(token=API_KEY)
restored_players = {}
restored_game = {}


def main():
    restored_players = {}
    if len(sys.argv) > 1:
        restored_game = secret_hitler.Game.load(sys.argv[1])
        for p in restored_game.players:
            restored_players[p.id] = p
    else:
        restored_game = None

    # Set up all command handlers

    updater = Updater(token=API_KEY)  # TODO init with bot=bot -> spooky errors?
    dispatcher = updater.dispatcher

    dispatcher.add_handler(get_static_handler("start"))
    dispatcher.add_handler(get_static_handler("help"))
    dispatcher.add_handler(get_static_handler("changelog"))
    dispatcher.add_handler(CommandHandler('feedback', feedback_handler, pass_args=True))

    dispatcher.add_handler(CommandHandler('newgame', newgame_handler, pass_chat_data=True))
    dispatcher.add_handler(CommandHandler('cancelgame', cancelgame_handler, pass_chat_data=True))
    dispatcher.add_handler(CommandHandler('leave', leave_handler, pass_user_data=True))

    dispatcher.add_handler(
        CommandHandler(secret_hitler.Game.ACCEPTED_COMMANDS + tuple(COMMAND_ALIASES.keys()), game_command_handler,
                       pass_chat_data=True, pass_user_data=True))
    dispatcher.add_handler(CommandHandler('savegame', save_game, pass_chat_data=True, pass_user_data=True))

    dispatcher.add_error_handler(handle_error)

    # allows viewing of exceptions
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO)  # not sure exactly how this works

    updater.start_polling()
    updater.idle()


def get_static_handler(command):
    """
    Given a string command, returns a CommandHandler for that string that
    responds to messages with the content of static_responses/[command].txt

    Throws IOError if file does not exist or something
    """

    f = open("static_responses/{}.txt".format(command), "r")
    response = f.read()

    return CommandHandler(command, \
                          (lambda bot, update: \
                               bot.send_message(chat_id=update.message.chat.id, text=response)))


def newgame_handler(bot, update, chat_data):
    """
    Create a new game (if doing so would overwrite an existing game in progress, only proceed if message contains "confirm")
    """
    game = chat_data.get("game_obj")

    chat_id = update.message.chat.id
    if update.message.chat.type == "private":
        bot.send_message(chat_id=chat_id, text="You can’t create a game in a private chat!")
    elif game is not None and game.game_state != secret_hitler.GameStates.GAME_OVER and update.message.text.find(
            "confirm") == -1:
        bot.send_message(chat_id=chat_id,
                         text="Warning: game already in progress here. Reply '/newgame confirm' to confirm")
    else:
        if game is not None:  # properly end that game
            game.set_game_state(secret_hitler.GameStates.GAME_OVER)
        chat_data["game_obj"] = secret_hitler.Game(chat_id)
        bot.send_message(chat_id=chat_id, text="Created game! /joingame to join, /startgame to start")


def cancelgame_handler(bot, update, chat_data):
    """
    Cancel a game.
    """
    game = chat_data.get("game_obj")

    chat_id = update.message.chat.id
    if game is not None:
        game.set_game_state(secret_hitler.GameStates.GAME_OVER)
        raise secret_hitler.GameOverException("Game cancelled. Type /newgame to start a new one.")
    else:
        bot.send_message(chat_id=chat_id, text="No game in progress here.")


def leave_handler(bot, update, user_data):
    """
    Forces a user to leave their current game, regardless of game state (could
    kill the game)
    """

    player_id = update.message.from_user.id
    # edge case: first message after restore is /leave
    global restored_players
    if player_id in list(restored_players.keys()):
        user_data["player_obj"] = restored_players[player_id]
        del restored_players[player_id]

    player = user_data.get("player_obj")

    if player is None or player.game is None:
        reply = "No game to leave!"
    else:
        player.leave_game(confirmed=True)
        reply = "Successfully left game!"

    if player is None:
        bot.send_message(chat_id=update.message.chat.id, text=reply)
    else:
        player.send_message(reply)


def parse_message(msg):
    """
    Helper function: split a messsage into its command and its arguments (two strings)
    """
    command = msg.split()[0]
    if command.endswith(bot.username):
        command = command[1:command.find("@")]
    else:
        command = command[1:]
    args = msg.split()[1:]
    if len(args) == 0:
        args = ""  # None
    else:
        args = " ".join(args)
    return command, args


COMMAND_ALIASES = {"nom": "nominate", "blam": "blame", "dig": "investigate", "log": "logs"}


def game_command_handler(bot, update, chat_data, user_data):
    """
    Pass all commands that secret_hitler.Game can handle to game's handle_message method
    Send outputs as replies via Telegram
    """
    command, args = parse_message(update.message.text)
    if command in list(COMMAND_ALIASES.keys()):
        command = COMMAND_ALIASES[command]
    player_id, chat_id = update.message.from_user.id, update.message.chat.id

    # Try to restore relevant save data (and mark this data as dirty)
    global restored_game
    global restored_players
    if restored_game is not None and restored_game.global_chat == chat_id:
        chat_data["game_obj"] = restored_game
        restored_game = None
    if player_id in list(restored_players.keys()):
        user_data["player_obj"] = restored_players[player_id]
        del restored_players[player_id]

    player = None
    game = None
    if "player_obj" in list(user_data.keys()):
        player = user_data["player_obj"]
    if "game_obj" in list(chat_data.keys()):
        game = chat_data["game_obj"]

    # game = ((player is not None) and player.game) or chat_data["game_obj"]
    if player is None:
        # this is a user's first interaction with the bot, so a Player
        # object must be created
        if game is None:
            bot.send_message(chat_id=chat_id, text="Error: no game in progress here. Start one with /newgame")
            return
        else:
            if args and (game.check_name(args) is None):  # args is a valid name
                player = secret_hitler.Player(player_id, args)
            else:
                # TODO: maybe also chack their Telegram first name for validity
                player = secret_hitler.Player(player_id, update.message.from_user.first_name)

            user_data["player_obj"] = player
    else:
        # it must be a DM or something, because there's no game in the current chat
        if game is None:
            game = player.game

        # I don't know how you can end up here
        if game is None:
            bot.send_message(chat_id=chat_id, text="Error: it doesn't look like you're currently in a game")
            return

    # at this point, 'player' and 'game' should both be set correctly

    try:
        reply = game.handle_message(player, command, args)

        # pass all supressed errors (if any) directly to the handler in
        # the order that they occurred
        while len(secret_hitler.telegram_errors) > 0:
            handle_error(bot, update, secret_hitler.telegram_errors.pop(0))
        # TODO: it would be cleaner to just have a consumer thread handling
        # these errors as they occur

        if reply:  # reply is None if no response is necessary
            bot.send_message(chat_id=chat_id, text=reply, parse_mode=telegram.ParseMode.MARKDOWN)

    except secret_hitler.GameOverException:
        return


# Credit (TODO: actual attribution): https://github.com/CaKEandLies/Telegram_Cthulhu/blob/master/cthulhu_game_bot.py#L63
def feedback_handler(bot, update, args=None):
    """
    Store feedback from users in a text file.
    """
    if args and len(args) > 0:
        feedback = open("ignore/feedback.txt", "a")
        feedback.write("\n")
        feedback.write(update.message.from_user.first_name)
        feedback.write("\n")
        # Records User ID so that if feature is implemented, can message them
        # about it.
        feedback.write(str(update.message.from_user.id))
        feedback.write("\n")
        feedback.write(" ".join(args))
        feedback.write("\n")
        feedback.close()
        bot.send_message(chat_id=update.message.chat_id,
                         text="Thanks for the feedback!")
    else:
        bot.send_message(chat_id=update.message.chat_id,
                         text="Format: /feedback [feedback]")


def handle_error(bot, update, error):
    try:
        raise error
    except TelegramError:
        logging.getLogger(__name__).warning('TelegramError! %s caused by this update: %s', error, update)


def save_game(bot, update, chat_data, user_data):
    game = None
    if "game_obj" in list(chat_data.keys()):
        game = chat_data["game_obj"]
    elif "player_obj" in list(user_data.keys()):
        game = user_data["player_obj"].game

    if game is not None:
        fname = "ignore/aborted_game.p"
        i = 0
        while os.path.exists(fname):
            fname = "ignore/aborted_game_{}.p".format(i)
            i += 1  # ensures multiple games can be saved

        game.save(fname)
        bot.send_message(chat_id=update.message.chat_id,
                         text="Saved game in current state as '{}'".format(fname))


if __name__ == "__main__":
    main()
