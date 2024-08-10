import logging
from json import JSONDecodeError
from botocore.exceptions import ClientError
from src.services.email_service import send_email
from src.config import config
from databases import Database
from src.database import post_table
import httpx

logger = logging.getLogger(__name__)


class APIResponseError(Exception):
    pass


async def send_text_email(to: str, subject: str, body: str):
    logger.debug(f"Sending email to '{to[:3]}' with subject '{subject[:20]}'")
    try:
        response = await send_email(to, subject, body)
    except ClientError as e:
        logger.error(e)
    else:
        logger.info(response)
        return response


async def send_user_registration_email(email: str, confirmation_url: str):
    return await send_text_email(
        email,
        "Successfully signed up",
        (
            f"Hi {email}! You have successfully signed up to the Service ReST API."
            " Please confirm your email by clicking on the"
            f" following link: {confirmation_url}"
        ),
    )


async def _generate_cute_creature_api(prompt: str):
    logger.debug("Generating cute creature")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "https://api.deepai.org/api/cute-creature-generator",
                data={"text": prompt},
                headers={"api-key": config.DEEPAI_API_KEY},
                timeout=60,
            )
            logger.debug(response)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as err:
            raise APIResponseError(
                f"API request failed with status code {err.response.status_code}"
            ) from err
        except (JSONDecodeError, TypeError) as err:
            raise APIResponseError("API response parsing failed") from err


async def generate_and_add_to_post(
    email: str,
    post_id: int,
    post_url: str,
    database: Database,
    prompt: str = "A blue british shorthair cat is sitting on a couch",
):
    try:
        response = await _generate_cute_creature_api(prompt)
    except APIResponseError as err:
        return await send_text_email(email, "Cute API request failed", str(err))

    logger.debug("connect to database to update post")

    query = (
        post_table.update()
        .where(post_table.c.id == post_id)
        .values(image_url=response["output_url"])
    )
    logger.debug(query)
    await database.execute(query)
    logger.debug("Database connection in backgrount task closed")

    await send_text_email(email, "Cute API request succeeded", response["output_url"])

    return response
