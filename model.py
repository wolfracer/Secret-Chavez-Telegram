from sqlalchemy import Column, Integer, Text, Boolean, ForeignKey, Enum, Table
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
import enum

Base = declarative_base()


# Basic enums

class GameState(enum.Enum):
    """Enum for the different states a game can be in."""

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


class Policy(enum.Enum):
    """Enum for a policy, can be either fascist or liberal."""
    F = 1
    L = 2

class Role(enum.Enum):
    """Enum for a role, can be either fascist, liberal or Hitler."""
    ROLE_FASCIST = 1
    ROLE_LIBERAL = 2
    ROLE_HITLER = 3


# Classes for the ORM

class Game(Base):
    """Main class. An instance represents a single game of Secret Hitler."""
    __tablename__ = "games"

    def __init__(self, chat_id):
        self.chat_id = chat_id

    def num_players(self):
        return(len(self.players))

    id = Column(Integer, primary_key=True)

    chat_id = Column(Integer, nullable=False)  # The group chat.

    players = relationship("Player", foreign_keys="[Player.game_id]", back_populates="game")  # The players participating.

    spectators = relationship("Spectator", back_populates="game")  # The spectators.

    cards = relationship("Card", back_populates="game")  # Cards on the deck.
    discards = relationship("Discard", back_populates="game")  # Discarded policies.

    president_id = Column(Integer, ForeignKey("players.id"))
    president = relationship("Player", foreign_keys="[Game.president_id]")  # Current president.

    chancellor_id = Column(Integer, ForeignKey("players.id"))
    chancellor = relationship("Player", foreign_keys="[Game.chancellor_id]")  # Current chancellor.

    last_nonspecial_president_id = Column(Integer, ForeignKey("players.id"))
    last_nonspecial_president = relationship("Player", foreign_keys="[Game.last_nonspecial_president_id]")

    time_logs = relationship("TimeLog")
    logs = relationship("Log")

    votes = relationship("Vote")

    vetoable_policy = Column(Enum(Policy))
    president_veto_vote = Column(Boolean)
    chancellor_veto_vote = Column(Boolean)

    liberal_policies = Column(Integer, default=0)
    fascist_policies = Column(Integer, default=0)
    anarchy_progress = Column(Integer, default=0)

    state = Column(Enum(GameState), default=GameState.ACCEPT_PLAYERS)

log_player_table = Table("association", Base.metadata,
    Column("log", Integer, ForeignKey("logs.id")),
    Column("player", Integer, ForeignKey("players.id"))
)

class Player(Base):
    """Represents a single player in a single game. If a person is in multiple games at the same time, multiple Player instances are needed."""
    __tablename__ = "players"

    def __init__(self, chat_id, name):
        self.chat_id = chat_id
        self.name = name

    def __str__(self):
        return self.name

    id = Column(Integer, primary_key=True)
    chat = Column(Integer)
    name = Column(Text, nullable=False)

    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    game = relationship("Game", foreign_keys=[game_id], back_populates="players")

    role = Column(Enum(Role))

    termlimited = Column(Boolean)
    confirmed_not_hitler = Column(Boolean)
    dead = Column(Boolean)

    known_logs = relationship("Log", secondary=log_player_table, back_populates="known_to")

class Spectator(Base):
    __tablename__ = "spectators"

    id = Column(Integer, primary_key=True)
    chat = Column(Integer)

    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    game = relationship("Game", back_populates="spectators")

class Card(Base):
    __tablename__ = "cards"

    id = Column(Integer, primary_key=True)

    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    game = relationship("Game", back_populates="discards")

    policy = Column(Enum(Policy))

class Discard(Base):
    __tablename__ = "discards"

    id = Column(Integer, primary_key=True)

    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    game = relationship("Game", back_populates="discards")

    policy = Column(Enum(Policy))


class Log(Base):
    __tablename__ = "logs"

    id = Column(Integer, primary_key=True)

    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    game = relationship("Game", back_populates="logs")

    message = Column(Text, nullable=False)

    # Only lists players, not spectators, they have to be handled seperately
    known_to = relationship("Player", secondary=log_player_table, back_populates="known_logs")
    known_to_group = Column(Boolean)

""" TODO Implement time logs
class TimeLog(Base):
    __tablename__ = "time_logs"

    id = Column(Integer, primary_key=True)

    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    game = relationship("Game", back_populates="time_logs")

    # time_logs : List<Map<GameState, Map<Player,Timestamp>>>
"""

class Vote(Base):
    """Represents a single vote."""
    __tablename__ = "votes"

    id = Column(Integer, primary_key=True)

    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    game = relationship("Game", back_populates="votes")

    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    player = relationship("Player")

    vote = Column(Boolean, nullable=False)
