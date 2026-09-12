import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

for handler in logger.handlers:
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        )
    )

from routes import route


def lambda_handler(event, context):
    return route(event)