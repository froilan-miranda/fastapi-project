import os
from typing import AsyncGenerator, Generator
from unittest.mock import Mock, AsyncMock

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport, Request, Response

# Override environment variable for testing
os.environ["ENV_STATE"] = "test"
from src.database import database, user_table  # noqa E402
from src.main import app  # noqa E402
from src.tests.helpers import create_post  # noqa E402


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture()
def client() -> Generator:
    yield TestClient(app)


@pytest.fixture(autouse=True)
async def db() -> AsyncGenerator:
    await database.connect()
    yield database
    await database.disconnect()


@pytest.fixture()
async def async_client(client) -> AsyncGenerator:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url=client.base_url
    ) as ac:
        yield ac


@pytest.fixture()
async def registered_user(async_client: AsyncClient) -> dict:
    user_details = {"email": "test@example.net", "password": "test"}

    await async_client.post("/register", json=user_details)
    query = user_table.select().where(user_table.c.email == user_details["email"])
    user = await database.fetch_one(query)
    user_details["id"] = user["id"]
    return user_details

@pytest.fixture()
async def confirmed_user(registered_user: dict) -> dict:
    query = (user_table.update().where(user_table.c.email == registered_user["email"]).values(confirmed=True))
    await database.execute(query)
    return registered_user

@pytest.fixture()
async def logged_in_token(async_client: AsyncClient, confirmed_user: dict) -> str:
    response = await async_client.post("/token", json=confirmed_user)
    return response.json()["access_token"]

@pytest.fixture(autouse=True)
def mock_httpx_client(mocker):
    """
    Fixture to mock the HTTPX client so that we never make any
    real HTTP requests (especially important when registering users).
    """
    mocked_client = mocker.patch("src.tasks.httpx.AsyncClient")

    mocked_async_client = Mock()
    response = Response(status_code=200, content="", request=Request("POST", "//"))
    mocked_async_client.post = AsyncMock(return_value=response)
    mocked_client.return_value.__aenter__.return_value = mocked_async_client

    return mocked_async_client

@pytest.fixture()
async def created_post(async_client: AsyncClient, logged_in_token: str):
    return await create_post("test", async_client, logged_in_token)


#@pytest.fixture(autouse=True)
#def mock_email_service(mocker):
    #mock_service = mocker.patch("src.services.email_service.send_email")
    #mock_service.return_value = {
        #'MessageId': '0100019133ced5dd-39cb4472-3493-4e27-8fb8-55dce45f7310-000000',   
        #'ResponseMetadata': {
            #'RequestId': 'a5c91545-312f-4f4c-a0f7-e6cca433c2f1', 
            #'HTTPStatusCode': 200, 
            #'HTTPHeaders': {
                #'date': 'Thu, 08 Aug 2024 21:04:38 GMT', 
                #'content-type': 'text/xml', 
                #'content-length': '326', 
                #'connection': 'keep-alive', 
                #'x-amzn-requestid': 'a5c91545-312f-4f4c-a0f7-e6cca433c2f1'
            #}, 
            #'RetryAttempts': 0
        #}
    #}
