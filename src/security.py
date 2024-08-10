import logging
import datetime
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, ExpiredSignatureError, JWTError
from typing import Annotated, Literal


from src.database import database, user_table

logger = logging.getLogger(__name__)

ALGORITHM = "HS256"
SECRET_KEY = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
pwd_context = CryptContext(schemes=["bcrypt"])

def create_credentials_exception(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )

def create_access_token(email:str):
    #logger.debug("Creating access token", extra={"email", email})
    expire = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=access_token_expire_minutes())
    jwt_data = { "sub": email, "exp": expire, "type": "access" }
    encode_jwt = jwt.encode(jwt_data, key=SECRET_KEY, algorithm=ALGORITHM)
    return encode_jwt

def create_confirm_token(email:str):
    #logger.debug("Creating confirmation token", extra={"email", email})
    expire = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=confirm_token_expire_minutes())
    jwt_data = { "sub": email, "exp": expire, "type": "confirmation" }
    encode_jwt = jwt.encode(jwt_data, key=SECRET_KEY, algorithm=ALGORITHM)
    return encode_jwt

def get_subject_for_token_type(token: str, type: Literal["access", "confirmation"]) -> str:
    try:
        payload =jwt.decode(token, key=SECRET_KEY, algorithms=[ALGORITHM])
    except ExpiredSignatureError as e:
        print("this should happen")
        raise create_credentials_exception("Token expired") from e
    except JWTError as e:
        raise create_credentials_exception("Invalid token") from e

    email = payload.get("sub")
    if email is None:
        raise create_credentials_exception("Token is missing 'sub' field")

    token_type = payload.get("type")
    if token_type is None or token_type != type:
        raise create_credentials_exception(f"Token has incorrect type, expected {type}, got {token_type}")
    return email

def access_token_expire_minutes() -> int:
    return 30

def confirm_token_expire_minutes() -> int:
    return 1440

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

async def get_user(email: str):
    #logger.debug("Fetching user from database", extra={"email", email})
    query = user_table.select().where(user_table.c.email == email)
    result = await database.fetch_one(query)
    if not result:
        return None
    return result

async def authenticate_user(email: str, password: str) -> bool:
    #logger.debug("Authenticating user", extra={"email": email})
    user = await get_user(email)
    if not user:
        raise create_credentials_exception("Could not find user for this email")
    if not verify_password(password, user.password):
        raise create_credentials_exception("Incorrect password")
    if not user.confirmed:
        raise create_credentials_exception("User has not confirmed email")
    return user


async def get_current_user(token:Annotated[str, Depends(oauth2_scheme)]):
    email = get_subject_for_token_type(token, "access")
    user = await get_user(email)
    if user is None:
        raise create_credentials_exception("Could not find user for this token")
    return user
