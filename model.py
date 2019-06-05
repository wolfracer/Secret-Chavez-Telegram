from sqlalchemy import *
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import *
import enum

Base = declarative_base()


class GameStates(enum.Enum):
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
    F = 1
    L = 2


class Party(enum.Enum):
    PARTY_FASCIST = 1
    PARTY_LIBERAL = 2


class Role(enum.Enum):
    ROLE_FASCIST = 1
    ROLE_LIBERAL = 2
    ROLE_HITLER = 3


class Player(Base):
    __tablename__ = "players"

    id = Column(Integer, primary_key=True)
    chat = Column(Integer)
    name = Column(Text, nullable=False)

    game_id = Column(Integer, ForeignKey("games.id"))

    party = Column(Enum(Party))
    role = Column(Enum(Role))

    spectator = Column(Boolean, default=false)


class Game(Base):
    __tablename__ = "games"

    id = Column(Integer, primary_key=True)

    chat = Column(Integer, nullable=False)

    # players = back populated from Player

    # discards = back populated from Discard

    president_id = Column(Integer, ForeignKey("players.id"))
    president = relationship("Player")
    chancellor_id = Column(Integer, ForeignKey("players.id"))
    chancellor = relationship("Player")

    # dummy players used for logs access
    spectator_id = Column(Integer, ForeignKey("players.id"), default=Player(name="spectators"))
    spectator = relationship("Player")
    group_id = Column(Integer, ForeignKey("players.id"), default=Player(name="everyone"))
    group = relationship("Player")

    last_nonspecial_president_id = Column(Integer, ForeignKey("players.id"))
    last_nonspecial_president = relationship("Player")

    vetoable_policy = Column(Enum(Policy))
    president_veto_vote = Column(Boolean)
    chancellor_veto_vote = Column(Boolean)

    num_players = Column(Integer, default=0)

    # votes = back populated from Vote
    liberal = Column(Integer, default=0)
    fascist = Column(Integer, default=0)
    anarchy_progress = Column(Integer, default=0)

    state = Column(Enum(GameStates), default=GameStates.ACCEPT_PLAYERS)


Player.game = relationship("Game", back_populates="players")  # add game to Player as it can't be added in player itself because Python needs it to be defined *before* usage, lol


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


class TimeLog(Base):
    __tablename__ = "time_logs"

    id = Column(Integer, primary_key=True)

    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    game = relationship("Game", back_populates="time_logs")

    # TODO time_logs :: [ GameState -> (Player -> timestamp) ]


class Vote(Base):
    __tablename__ = "votes"

    id = Column(Integer, primary_key=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    game = relationship("Game", back_populates="votes")
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    player = relationship("Player")
    vote = Column(Boolean, nullable=False)
    termlimited = Column(Boolean)
    confirmed_not_hitler = Column(Boolean)
    dead = Column(Boolean)
