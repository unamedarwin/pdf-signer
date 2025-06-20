PDFSigner

A simple Flask service for digitally signing PDFs using a PKCS#12 certificate (.pfx) and a public Time-Stamping Authority (TSA). Runs inside Docker and exposes a /sign-pdf endpoint.

---

## Features

- Sign any uploaded PDF (application/pdf) with a .pfx certificate
- Add a trusted timestamp from a public TSA
- Retry signing with configurable attempts and exponential backoff
- Enforce maximum upload size and validate PDF magic header
- Structured JSON logging with per-request UUID
- Healthcheck endpoint for orchestrators (e.g., Kubernetes, Docker Swarm)
- Runs under Gunicorn in production with a lightweight Docker image

---

## Prerequisites

- Docker ≥ 20.10
- (Optional) Python 3.11 for local development

---

## Environment Variables

| Name | Description | Default |
|----------------------|------------------------------------------------------------|-------------------|
| TSA_URL | URL of the Time-Stamping Authority | http://freetsa.org/tsr |
| MAX_RETRIES | Maximum number of signing attempts | 5 |
| INITIAL_DELAY | Seconds to wait before the first retry | 2 |
| MAX_DELAY | Maximum seconds between retries (exponential backoff) | 30 |
| MAX_CONTENT_LENGTH | Maximum upload size in bytes | 10485760 (10 MB)|
| FLASK_ENV | Flask environment (development or production) | production |

---

## Building the Docker Image

From the project root (where the Dockerfile is located):

bash docker build -t pdfsigner:latest . 

---

## Running with Docker

1. If a container named pdfsigner is already running, stop and remove it:

bash docker stop pdfsigner docker rm pdfsigner 

2. Run the container:

bash docker run -d \ --name pdfsigner \ -p 8000:8000 \ -e TSA_URL="http://freetsa.org/tsr" \ -e MAX_RETRIES="5" \ -e INITIAL_DELAY="2" \ -e MAX_DELAY="30" \ -e MAX_CONTENT_LENGTH="10485760" \ pdfsigner:latest 

3. View logs in real time:

bash docker logs -f pdfsigner 

---

## API Usage

### Healthcheck

GET /healthz 

Response:

json { "status": "ok" } 

### Sign a PDF

POST /sign-pdf Content-Type: multipart/form-data Form fields: - file: PDF file (`.pdf`) - cert: PKCS#12 certificate file (`.pfx`) - password: (optional) password for the .pfx 

Successful Response: Returns signed.pdf as an attachment.

Errors:
- 400 if file or cert is missing, upload is too large, or the file is not a valid PDF
- 400 if the .pfx cannot be loaded
- 500 if signing fails after MAX_RETRIES

#### Example with curl

bash curl -X POST http://localhost:8000/sign-pdf \ -F file=@document.pdf \ -F cert=@mycert.pfx \ -F password="yourPassword" \ --output signed.pdf 

---

## Local Development

1. Create and activate a Python virtual environment:

bash python3.11 -m venv venv source venv/bin/activate pip install -r requirements.txt 

2. Start the Flask development server:

bash export FLASK_ENV=development export TSA_URL="http://freetsa.org/tsr" flask run --host=0.0.0.0 --port=8000 

3. Use POST /sign-pdf as described above.

---

## Testing & Quality

- It is recommended to add pytest tests for:
- Loading .pfx certificates with and without password
- Signing valid and invalid PDFs (mocking the TSA)
- Use pre-commit hooks for code quality with Black, Flake8, and MyPy

---

## License

MIT © 2025





