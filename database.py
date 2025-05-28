from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, create_engine, func
from sqlalchemy.orm import sessionmaker, relationship, declarative_base
from datetime import datetime, timezone

DATABASE_URL = "sqlite:///./app.db"
engine = create_engine(DATABASE_URL)

session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class History(Base):
    __tablename__ = "history"
    id = Column(Integer, primary_key=True, index=True)
    city = Column(String)
    user_session = Column(String)
    time = Column(DateTime, default=datetime.now(timezone.utc))

Base.metadata.create_all(bind=engine)

def add_history(city: str, user_session: str):
    db = session_local()
    history_entry = History(city=city, user_session=user_session)
    db.add(history_entry)
    db.commit()
    db.refresh(history_entry)
    db.close()
    return history_entry

def get_history(user_session: str):
    db = session_local()
    history = db.query(History).filter(History.user_session == user_session).all()
    db.close()
    return history

def get_last_history(user_session: str):
    db = session_local()
    history = db.query(History).filter(History.user_session == user_session).order_by(History.time.desc()).first()
    db.close()
    return history


def get_location_statistics():
    db = session_local()
    stats = (
        db.query(History.city, func.count(History.id))
        .group_by(History.city)
        .order_by(func.count(History.id).desc())
        .all()
    )
    return stats
    db.close()