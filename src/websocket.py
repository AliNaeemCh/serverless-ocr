import json
import boto3

from config import config
import logging
logger = logging.getLogger(__name__)


websocket_client = boto3.client(
    "apigatewaymanagementapi",
    endpoint_url=config.WEBSOCKET_ENDPOINT,
)



from botocore.exceptions import ClientError

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

    except ClientError as e:

        error_code = e.response.get("Error", {}).get("Code")

        if error_code == "GoneException":
            logger.warning(
                "WebSocket connection is gone: %s",
                connection_id,
            )
            return False

        logger.exception(
            "Failed to send WebSocket message (connection_id=%s)",
            connection_id,
        )
        raise

    except Exception:
        logger.exception(
            "Unexpected WebSocket error (connection_id=%s)",
            connection_id,
        )
        raise
