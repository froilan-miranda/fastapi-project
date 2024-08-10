import logging
from enum import Enum
from typing import Annotated
from fastapi import Depends, APIRouter, HTTPException, Request, BackgroundTasks
import sqlalchemy
from src.database import database, post_table, comment_table, like_table
from src.models.post import (
    UserPost,
    UserPostIn,
    Comment,
    CommentIn,
    PostLikeIn,
    PostLike,
    UserPostWithComments,
    UserPostWithLikes,
)
from src.models.user import User
from src.security import get_current_user
from src.tasks import generate_and_add_to_post


router = APIRouter()

logger = logging.getLogger(__name__)

logger.info("Initializing post router")

select_post_and_likes = (
    sqlalchemy.select(post_table, sqlalchemy.func.count(like_table.c.id).label("likes"))
    .select_from(post_table.outerjoin(like_table))
    .group_by(post_table.c.id)
)


async def find_post(post_id: int):
    logger.info(f"Find post with id: {post_id}")
    query = post_table.select().where(post_table.c.id == post_id)
    logger.debug(query)
    return await database.fetch_one(query)


@router.get("/")
async def root():
    return {"message": "Alive!"}


@router.post("/post", response_model=UserPost, status_code=201)
async def create_post(post: UserPostIn, current_user: Annotated[User, Depends(get_current_user)], background_tasks: BackgroundTasks, request: Request, prompt: str = None):
    logger.info("Create post")
    #data = post.model_dump()
    data = {**post.model_dump(), "user_id": current_user.id}
    query = post_table.insert().values(data)
    logger.debug(query)
    last_record_id = await database.execute(query)

    if prompt:
        background_tasks.add_task(
            generate_and_add_to_post,
            current_user.email,
            post_id=last_record_id,
            post_url=request.url_for("get_post_with_comments", post_id=last_record_id),
            database=database,
            prompt=prompt
        )
    return {**data, "id": last_record_id}


class PostSorting(str, Enum):
    new = "new",
    old = "old",
    most_likes = "most_likes"


@router.get("/post", response_model=list[UserPostWithLikes])
async def get_all_posts(sorting: PostSorting = PostSorting.new):
    logger.info("Get all posts")

    match sorting:
        case PostSorting.new:
            query = select_post_and_likes.order_by(post_table.c.id.desc())
        case PostSorting.old:
            query = select_post_and_likes.order_by(post_table.c.id.asc())
        case PostSorting.most_likes:
            query = select_post_and_likes.order_by(sqlalchemy.desc("likes"))

    logger.debug(query)
    return await database.fetch_all(query)


@router.post("/comment", response_model=Comment, status_code=201)
async def create_comment(comment: CommentIn, current_user: Annotated[User, Depends(get_current_user)]):
    logger.info("Create comment")
    post = await find_post(comment.post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    #data = comment.model_dump()
    data = {**comment.model_dump(), "user_id": current_user.id}
    query = comment_table.insert().values(data)
    last_record_id = await database.execute(query)
    return {**data, "id": last_record_id}


@router.get("/post/{post_id}/comment", response_model=list[Comment])
async def get_comments_on_post(post_id: int):
    logger.info(f"Get comments on post with id: {post_id}")
    query = comment_table.select().where(comment_table.c.post_id == post_id)
    logger.debug(query)
    return await database.fetch_all(query)


@router.get("/post/{post_id}", response_model=UserPostWithComments)
async def get_post_with_comments(post_id: int):
    logger.info(f"Get post with comments with id: {post_id}")
    query = select_post_and_likes.where(post_table.c.id == post_id)
    logger.debug(query)
    post = await database.fetch_one(query)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    return {"post": post, "comments": await get_comments_on_post(post_id)}


@router.post("/like", response_model=PostLike, status_code=201)
async def like_post(like: PostLikeIn, current_user: Annotated[User, Depends(get_current_user)]):
    logger.info("Like post")
    post = await find_post(like.post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    data = {**like.model_dump(), "user_id": current_user.id}
    query = like_table.insert().values(data)
    logger.debug(query)
    last_record_id = await database.execute(query)
    return {**data, "id": last_record_id}

