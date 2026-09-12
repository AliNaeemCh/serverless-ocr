import json
import boto3

from config import config


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

    websocket_client.post_to_connection(
        ConnectionId=connection_id,
        Data=json.dumps(message).encode("utf-8"),
    )