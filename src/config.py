from dotenv import load_dotenv
import os


load_dotenv()


class Config:

    GEMINI_API_KEY: str = os.environ[
        "GEMINI_API_KEY"
    ]

    MODEL = os.environ[
        "MODEL"
    ]

    FALLBACK_MODEL = os.environ[
        "FALLBACK_MODEL"
    ]

    MAX_CONCURRENCY = int(
        os.environ[
            "MAX_CONCURRENCY"
        ]
    )

    WEBSOCKET_ENDPOINT = os.environ[
        "WEBSOCKET_ENDPOINT"
    ]


config = Config()