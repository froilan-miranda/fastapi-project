import logging
import boto3
from botocore.exceptions import ClientError
from src.config import config

logger = logging.getLogger(__name__)

ses_client = boto3.client(
    service_name="ses",
    region_name=config.AWS_REGION_NAME,
    aws_access_key_id=config.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=config.AWS_SECRET_ACCESS_KEY,
)

#async def send_email(subject: str, body: str, recipients: list[str]) -> None:
async def send_email(to: str, subject: str, body: str) -> None:
    logger.info("Sending email")
    response = ses_client.send_email(
        Destination={
            'ToAddresses': [
                to
            ],
        },
        Message={
            'Body': {
                'Text': {
                    'Charset': 'UTF-8',
                    'Data': body,
                },
            },
            'Subject': {
                'Charset': 'UTF-8',
                'Data': subject,
            },
        },
        Source='froilan@virtual-artifact.com',
    )

    return response
