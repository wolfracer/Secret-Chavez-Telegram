from model import *
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine('sqlite:///:memory:', echo=True)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()

test_game = Game(chat_id=123)
session.add(test_game)
test_player = Player(name="Richard", game=test_game)
session.add(test_player)

#print(session.query(Player).filter_by(name="Richard").first())

session.commit()
