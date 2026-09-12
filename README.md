# Serverless OCR

A compact serverless GenAI workload covering concurrent processing, bounded resource usage, Gemini retries and model fallback, ephemeral storage, and real-time client communication.

The application accepts a PDF or image, extracts its contents into structured HTML with LaTeX support, and reports page-level progress to the UI while processing.

## Architecture

```text
                         ┌──────────────────────┐
                         │      React UI        │
                         │                      │
                         └──────────┬───────────┘
                                    │
                    ┌───────────────┴────────────────┐
                    │                                │
                 HTTP API                       WebSocket API
                    │                                │
                    ▼                                ▼
             ┌──────────────┐                ┌──────────────┐
             │ API Gateway  │                │ API Gateway  │
             │  HTTP API    │                │  WebSocket   │
             └──────┬───────┘                └──────┬───────┘
                    │                                │
                    └───────────────┬────────────────┘
                                    ▼
                            ┌──────────────┐
                            │    Lambda    │
                            │ Python 3.14  │
                            └──────┬───────┘
                                   │
                     ┌─────────────┼─────────────┐
                     │             │             │
                     ▼             ▼             ▼
                  /tmp          PyMuPDF      Gemini Vision
                                  │
                            concurrent page
                              processing
```

* **Dual API Protocols:** Document uploads and HTML responses over HTTP; page-level progress over WebSocket.

* **Transient File Operations:** Uses Lambda `/tmp` for uploads and PDF rendering without external storage.

* **Bounded Parallelism:** Processes PDF pages concurrently with `asyncio` and `httpx`, controlled by a configurable concurrency limit.

* **Vision-Based Extraction:** Gemini Vision extracts text, layout, multi-column content, and tables into structured HTML with LaTeX support.

* **Resilient Requests:** Retry and exponential backoff with jitter, provider-supplied retry delays, quota detection, and primary/fallback model handling.

* **Dependency Isolation:** Third-party dependencies are packaged as a Lambda Layer built against the Lambda Python 3.14 runtime.

## Stack

* AWS Lambda · Python 3.14

* API Gateway HTTP API

* API Gateway WebSocket API

* Gemini Vision

* `httpx`

* PyMuPDF

* Docker

* AWS Lambda Layers

## Deployment

### AWS Resources

Configure the API Gateway routes to invoke the Lambda function:

```text
HTTP API

└── POST /start → Lambda

WebSocket API

├── $connect    → Lambda

├── $disconnect → Lambda

└── getConnId   → Lambda
```

### Environment Variables

```text
GEMINI_API_KEY=<your-gemini-api-key>

MODEL=<primary-gemini-model>

FALLBACK_MODEL=<fallback-gemini-model>

MAX_CONCURRENCY=5

WEBSOCKET_ENDPOINT=https://<api-id>.execute-api.<region>.amazonaws.com/<stage>
```

`WEBSOCKET_ENDPOINT` is the API Gateway Management API endpoint used by Lambda to send messages to connected clients.

### Lambda Layer

Build the dependency layer against the Lambda Python 3.14 runtime:

```powershell
New-Item -ItemType Directory -Force layer-build | Out-Null

docker run --rm --entrypoint /bin/bash `
  -v "${PWD}:/var/task" `
  public.ecr.aws/lambda/python:3.14 `
  -c "mkdir -p /var/task/layer-build/python && pip install -r /var/task/requirements.txt -t /var/task/layer-build/python"

Compress-Archive -Path layer-build\python -DestinationPath layer.zip -Force

Remove-Item -Recurse -Force layer-build
```

Publish the layer:

```powershell
aws lambda publish-layer-version `
  --layer-name serverless-ocr-dependencies `
  --zip-file fileb://layer.zip `
  --compatible-runtimes python3.14
```

Attach the published layer version to the Lambda function.

### Lambda Function

Package the application:

```powershell
Compress-Archive -Path src\* -DestinationPath lambda.zip -Force
```

Upload `lambda.zip` to the Lambda function.

Handler:

```text
handler.lambda_handler
```

### Dependencies

```text
httpx

python-dotenv

PyMuPDF
```

`boto3` is provided by the Lambda runtime.

## Integration

The frontend consumes the backend through the two API interfaces:

```text
                    WebSocket
                       │
                       ▼
                  getConnId
                       │
                       ▼
                 connection ID
                       │
                       │
                       ▼
HTTP ────────────► POST /start
                       │
                       ▼
                    Lambda
                    /     \
                   /       \
                  ▼         ▼
        WebSocket progress  HTTP response
                              │
                              ▼
                         Final HTML
```

HTTP API:

```text
https://<http-api-id>.execute-api.<region>.amazonaws.com/start
```

WebSocket API:

```text
wss://<websocket-api-id>.execute-api.<region>.amazonaws.com/<stage>
```

The frontend is maintained separately. Its [repository](https://github.com/AliNaeemCh/serverless-ocr-frontend) contains the React implementation and client-side workflow for connecting to these APIs, uploading documents, receiving progress updates, and rendering the resulting HTML and LaTeX.