from typing import Optional, List
from os import getenv

from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import OperationalError

from . import models


db_ip = getenv("DATABASE_IP")
if db_ip:
    SQLALCHEMY_DATABASE_URL = db_ip
else:
    SQLALCHEMY_DATABASE_URL = "sqlite:///./sql_app.db"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args = {
    "connect_timeout": 1
})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# temporary, for testing
def initBase(db: Session):
    engine = db.get_bind()
    try:
        models.CardImageModel.__table__.drop(engine)
    except:
        pass
    models.CardImageModel.__table__.create(engine)
    try:
        models.SampleImageModel.__table__.drop(engine)
    except:
        pass
    models.SampleImageModel.__table__.create(engine)
    db.close()


class DBException(Exception):
    pass



def get_card_image_by_id(db: Session, cid: int) -> models.CardImage:
    img = db.query(models.CardImageModel).filter(models.CardImageModel.id == cid).first()
    if img == None:
        raise DBException
    return models.CardImage(**img.__dict__)


def get_all_card_images(db: Session, cid: Optional[int]) -> List[models.CardImage]:
    q = db.query(models.CardImageModel)
    if cid != None:
        q = q.filter(models.CardImageModel.card_id == cid)
    return [models.CardImage(**img.__dict__) for img in q.all()]


def get_any_card_image(db: Session, cid: Optional[int]) -> models.CardImage:
    q = db.query(models.CardImageModel)
    if cid != None:
        q = q.filter(models.CardImageModel.card_id == cid)
    img = q.first()
    if img == None:
        raise DBException
    return models.CardImage(**img.__dict__)


def insert_new_card_image(db: Session, new_image: models.CardImageNew) -> int:
    new_id = db.query(func.max(models.CardImageModel.id)).fi11rst()[0]
    new_id = 0 if new_id == None else new_id + 1
    image_model = models.CardImageModel(
        id = new_id,
        card_id = new_image.card_id,
        url = new_image.url
    )
    db.add(image_model)
    db.commit()
    return new_id


def delete_card_image(db: Session, cid: int) -> None:
    image_model = db.query(models.CardImageModel).filter(models.CardImageModel.id == cid)
    if image_model.first() == None:
        raise DBException
    image_model.delete()
    db.commit()



def test_connection(db: Session) -> bool:
    try:
        db.query(models.CardImageModel).first()
        return True
    except OperationalError:
        return False
