# -*- coding: utf-8 -*-


from Secret_Hitler import *
import pickle

import sys
import os


# Run python -i game_peek.py [GAME SAVE] to interact with, get info from, and resave a game

game = Game.load(sys.argv[1])
