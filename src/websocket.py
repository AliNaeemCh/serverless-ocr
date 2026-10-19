import json
import boto3

from config import config
import logging
logger = logging.getLogger(__name__)


websocket_client = boto3.client(
    "apigatewaymanagementapi",
    endpoint_url=config.WEBSOCKET_ENDPOINT,
)


def send_websocket_message(
    connection_id,
    message,
):
    """
    Send a message to the browser through
    API Gateway WebSocket.
    """

    try:
        websocket_client.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps(message).encode("utf-8"),
        )

        return True

    except Exception:
        logger.exception(
            "Failed to send WebSocket message (connection_id=%s). "
            "Continuing processing.",
            connection_id,
        )
        return False
