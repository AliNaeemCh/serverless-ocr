import os
import base64
import asyncio
import json
import logging

from websocket import send_websocket_message
from document_service import process_document
from files import save_uploaded_file


logger = logging.getLogger(__name__)


def route(event):

    route_key = event.get(
        "requestContext", {}
    ).get("routeKey")

    # =========================
    # WebSocket: $connect
    # =========================

    if route_key == "$connect":

        connection_id = event["requestContext"]["connectionId"]

        logger.info(
            "WebSocket connected: %s",
            connection_id,
        )

        return {
            "statusCode": 200,
            "body": "Connected",
        }

    # =========================
    # WebSocket: $disconnect
    # =========================

    if route_key == "$disconnect":

        connection_id = event["requestContext"]["connectionId"]

        logger.info(
            "WebSocket disconnected: %s",
            connection_id,
        )

        return {
            "statusCode": 200
        }

    # =========================
    # WebSocket: getConnId
    # =========================

    if route_key == "getConnId":

        connection_id = event["requestContext"]["connectionId"]

        logger.info(
            "Registering connection: %s",
            connection_id,
        )

        message = {
            "type": "connection",
            "connectionId": connection_id,
        }

        send_websocket_message(
            connection_id=connection_id,
            message=message,
        )

        return {
            "statusCode": 200,
            "body": "Registered",
        }

    # =========================
    # HTTP: POST /start
    # =========================

    method = (
        event.get("requestContext", {})
        .get("http", {})
        .get("method")
    )

    raw_path = event.get("rawPath")

    if method == "POST" and raw_path == "/start":

        file_path = None
        connection_id = None

        try:

            body = event.get("body")

            if body is None:
                raise ValueError(
                    "Request body is missing"
                )

            if event.get("isBase64Encoded", False):
                body = base64.b64decode(body).decode("utf-8")

            data = json.loads(body)

            connection_id = data.get("connectionId")

            if not connection_id:
                raise ValueError(
                    "WebSocket connectionId is required"
                )

            file_path = save_uploaded_file(
                event,
                filename=data.get("filename"),
            )

            html = asyncio.run(
                process_document(
                    file_path,
                    connection_id,
                )
            )

            send_websocket_message(
                connection_id,
                {
                    "status": "completed",
                },
            )

            return {
                "statusCode": 200,
                "body": json.dumps({
                    "status": "completed",
                    "html": html,
                }),
            }

        except Exception:

            logger.exception(
                "File processing failed"
            )

            if connection_id:
                try:
                    send_websocket_message(
                        connection_id,
                        {
                            "status": "error",
                            "error": "Something went wrong",
                        },
                    )
                except Exception:
                    logger.exception(
                        "Failed to send WebSocket error"
                    )

            return {
                "statusCode": 500,
                "body": json.dumps({
                    "status": "error",
                    "error": "Something went wrong",
                }),
            }

        finally:

            if file_path and os.path.exists(file_path):
                os.remove(file_path)

                logger.info(
                    "Temporary file removed"
                )

    return {
        "statusCode": 400,
        "body": json.dumps({
            "error": "Invalid request",
        }),
    }