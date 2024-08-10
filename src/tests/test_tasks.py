import pytest
from databases import Database
from src.database import post_table
from src.tasks import APIResponseError, _generate_cute_creature_api, generate_and_add_to_post
import httpx

# @pytest.mark.anyio
# async def test_send_text_email(mock_email_service):
# await send_text_email("test@example.com", "test subject", "test body")
# mock_email_service.send_email.assert_called_once()


@pytest.mark.anyio
async def test_generate_cute_creature_api_success(mock_httpx_client):
    json_data = {"output_url": "http://example.com/image.jpg"}

    mock_httpx_client.post.return_value = httpx.Response(
        status_code=200, json=json_data, request=httpx.Request("POST", "//")
    )

    result = await _generate_cute_creature_api("a cat")

    assert result == json_data


@pytest.mark.anyio
async def test_generate_cute_creature_api_server_error(mock_httpx_client):
    mock_httpx_client.post.return_value = httpx.Response(
        status_code=500, content="", request=httpx.Request("POST", "//")
    )

    with pytest.raises(
        APIResponseError, match="API request failed with status code 500"
    ):
        await _generate_cute_creature_api("A cat")


@pytest.mark.anyio
async def test_generate_cute_creature_api_json_error(mock_httpx_client):
    mock_httpx_client.post.return_value = httpx.Response(
        status_code=200, content="Not JSON", request=httpx.Request("POST", "//")
    )

    with pytest.raises(APIResponseError, match="API response parsing failed"):
        await _generate_cute_creature_api("A cat")


@pytest.mark.anyio
async def test_generate_and_add_to_post_success(
    mock_httpx_client, created_post: dict, confirmed_user: dict, db: Database
):
    json_data = {"output_url": "https://example.com/image.jpg"}

    mock_httpx_client.post.return_value = httpx.Response(
        status_code=200, json=json_data, request=httpx.Request("POST", "//")
    )

    await generate_and_add_to_post(
        confirmed_user["email"], created_post["id"], "/post/1", db, "A cat"
    )

    # Check that after the background task runs, the post has been updated
    query = post_table.select().where(post_table.c.id == created_post["id"])

    updated_post = await db.fetch_one(query)

    assert updated_post.image_url == json_data["output_url"]
