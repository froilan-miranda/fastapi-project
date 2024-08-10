import logging
from fastapi import APIRouter, BackgroundTasks, HTTPException, status, Request
from src.models.user import UserIn
from src.security import get_password_hash, get_user, authenticate_user, create_access_token, get_subject_for_token_type, create_confirm_token
from src.database import database, user_table
from src import tasks

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/register", status_code=201)
async def register(user: UserIn, background_tasks: BackgroundTasks, request: Request):
    if await get_user(user.email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User already exists")

    hashed_password = get_password_hash(user.password)
    query = user_table.insert().values(email=user.email, password=hashed_password)

    logger.debug(query)

    await database.execute(query)

    logger.debug("Submitting background task to send email")
    background_tasks.add_task(
        tasks.send_user_registration_email,
        user.email, 
        confirmation_url=request.url_for("confirm_email", token=create_confirm_token(user.email)))
    return {
        "detail": "User created. Please confirm email.", 
    }


@router.post("/token")
async def login(user: UserIn):
    user = await authenticate_user(user.email, user.password)
    access_token = create_access_token(user.email)
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/confirm/{token}")
async def confirm_email(token: str):
    email = get_subject_for_token_type(token, "confirmation")
    query = user_table.update().where(user_table.c.email == email).values(confirmed=True)
    logger.debug(query)
    await database.execute(query)
    return {"detail": "User confirmed"}
