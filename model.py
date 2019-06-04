from sqlalchemy import *
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import *

Base = declarative_base()


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


class Player(Base):
    __tablename__ = "players"

    id = Column(Integer, primary_key=True)
    chat = Column(Integer)
    name = Column(Text, nullable=False)

    game_id = Column(Integer, ForeignKey("games.id"))
    game = relationship("Game", back_populates="players")

    party = Column(Text)
    role = Column(Text)


class Game(Base):
    __tablename__ = "games"

    id = Column(Integer, primary_key=True)

    chat = Column(Integer, nullable=False)

    # players = back populated from Player

    self.discard = []

    self.president = None
    self.chancellor = None
    self.termlimited_players = set()
    self.dead_players = set()
    self.confirmed_not_hitlers = set()

    # dummy players used for logs access
    spectator_id = Column(Integer, ForeignKey("players.id"), default=Player(name="spectators"))
    spectator = relationship("Player")
    group_id = Column(Integer, ForeignKey("players.id"), default=Player(name="everyone"))
    group = relationship("Player")

    self.spectators = set()
    self.logs = []  # [(message, [known_to])]
    self.time_logs = []  # [ GameState -> (Player -> timestamp) ]

    self.last_nonspecial_president = None
    self.vetoable_polcy = None
    self.president_veto_vote = None
    self.chancellor_veto_vote = None

    num_players = Column(Integer, default=0)

    # votes = back populated from Vote
    liberal = Column(Integer, default=0)
    fascist = Column(Integer, default=0)
    anarchy_progress = Column(Integer, default=0)

    state = Enum(GameStates, default=GameStates.ACCEPT_PLAYERS)


class Vote(Base):
    __tablename__ = "votes"

    id = Column(Integer, primary_key=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    game = relationship("Game", back_populates="votes")
    vote = Column(Boolean, nullable=False)
