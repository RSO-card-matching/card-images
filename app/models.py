# pylint: disable=no-name-in-module

from typing import Optional

from pydantic import BaseModel
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Boolean, Column, Integer, String


Base = declarative_base()


class CardImage(BaseModel):
    id: int
    card_id: int
    url: str

class CardImageNew(BaseModel):
    card_id: int
    url: str

class NewImageID(BaseModel):
    id: int


class CardImageModel(Base):
    __tablename__ = "card-images"
    id = Column(Integer, primary_key = True, index = True)
    card_id = Column(Integer, index = True)
    url = Column(String)

class SampleImageModel(Base):
    __tablename__ = "sample-images"
    id = Column(Integer, primary_key = True, index = True)
    sample_id = Column(Integer, index = True)
    url = Column(String)
