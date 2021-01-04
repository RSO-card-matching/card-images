# pylint: disable=no-name-in-module

from datetime import datetime, timedelta
from typing import Optional, List, Union
from os import getenv
import requests

from fastapi import Depends, FastAPI, File, Form, HTTPException, Path, status, UploadFile
from fastapi.security import OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from starlette.responses import RedirectResponse

from . import models, database


SECRET_KEY = getenv("OAUTH_SIGN_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

if (SECRET_KEY == None):
    print("Please define OAuth signing key!")
    exit(-1)

# fastAPI dependecy magic
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# init testing DB
# database.initBase(database.SessionLocal())

if (getenv("OAUTH_TOKEN_PROVIDER") == None):
    print("Please provide token provider URL!")
    exit(-1)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl = getenv("OAUTH_TOKEN_PROVIDER") + "/tokens")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex = r"(http.*localhost.*|https?:\/\/.*cardmatching.ovh.*)",
    allow_credentials = True,
    allow_methods = ["*"],
    allow_headers = ["*"],
)



async def get_current_user_from_token(token: str = Depends(oauth2_scheme)) -> int:
    credentials_exception = HTTPException(
        status_code = status.HTTP_401_UNAUTHORIZED,
        detail = "Could not validate credentials",
        headers = {"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms = [ALGORITHM])
        uid: Optional[int] = int(payload.get("sub"))
        if uid is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    return uid



@app.get("/v1/card-images", response_model = List[models.CardImage])
async def return_all_card_images(card_id: Optional[int] = None,
        current_user: int = Depends(get_current_user_from_token),
        db: Session = Depends(get_db)):
    return database.get_all_card_images(db, card_id)


@app.get("/v1/card-images/any")
async def return_any_card_image(card_id: Optional[int] = None,
        current_user: int = Depends(get_current_user_from_token),
        db: Session = Depends(get_db)):
    try:
        img = database.get_any_card_image(db, card_id)
        return RedirectResponse(img.url)
    except database.DBException:
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND,
            detail = "No suitable image found",
        )


@app.get("/v1/card-images/{image_id}")
async def return_specific_card_image(current_user: int = Depends(get_current_user_from_token),
        image_id: str = Path(...),
        db: Session = Depends(get_db)):
    try:
        img = database.get_card_image_by_id(db, image_id)
        return RedirectResponse(img.url)
    except database.DBException:
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND,
            detail = "Image with given ID not found"
        )


@app.post("/v1/card-images", response_model = models.NewImageID)
async def upload_new_card_image(card_id: int,
        image: UploadFile = File(...),
        current_user: int = Depends(get_current_user_from_token),
        db: Session = Depends(get_db)):
    r = requests.post(
        "https://s-ul.eu/api/v1/upload",
        data = {
            "wizard": "true",
            "key": getenv("S_UL_KEY")
        },
        files = {"file": image.file}
    )
    if r.status_code != 200:
        print("s-ul error:", end = " ")
        print(r.content)
        raise HTTPException(
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail = "Couldn't upload image"
        )
    img_url = r.json()["url"]
    new_id = database.insert_new_card_image(
        db,
        models.CardImageNew(card_id = card_id, url = img_url)
    )
    return models.NewImageID(id = new_id)


@app.delete("/v1/card-images/{image_id}", response_model = None)
async def remove_card_image(image_id: int = Path(...),
        current_user: int = Depends(get_current_user_from_token),
        db: Session = Depends(get_db)):
    try:
        img = database.get_card_image_by_id(db, image_id)
        name = img.url.split("/")[-1]
        r = requests.get(f"https://s-ul.eu/delete.php?key={getenv('S_UL_KEY')}&file={name}")
        if r.status_code != 200:
            print("s-ul error:", end = " ")
            print(r.status_code)
        database.delete_card_image(db, image_id)
    except database.DBException:
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND,
            detail = "Image with given ID not found"
        )



@app.get("/health/live", response_model = str)
async def liveness_check():
    return "OK"


@app.get("/health/ready", response_model = dict)
async def readiness_check(db: Session = Depends(get_db)):
    if database.test_connection(db):
        try:
            requests.get(getenv("OAUTH_TOKEN_PROVIDER") + "/tokens", timeout = 1.)
            return {
                "database": "OK",
                "token_provider": "OK"
            }
        except requests.exceptions.Timeout:
            raise HTTPException(
                status_code = status.HTTP_503_SERVICE_UNAVAILABLE,
                detail = "Token provider down",
            )
    else:
        raise HTTPException(
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE,
            detail = "Database down",
        )
