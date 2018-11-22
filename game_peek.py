# -*- coding: utf-8 -*-


from secret_hitler import *
import sys

# Run python -i game_peek.py [GAME SAVE] to interact with, get info from, and resave a game

game = Game.load(sys.argv[1])
