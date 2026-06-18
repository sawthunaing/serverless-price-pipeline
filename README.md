# Serverless Price-Data Pipeline on AWS

An event-driven, serverless data pipeline that ingests price data from CSV files, processes and stores it reliably, and serves it through a REST API. Built end-to-end on AWS with retry handling and failure alerting.

This mirrors the kind of data platform a price-reporting agency runs: ingest data files, process them reliably, store them, and deliver them to clients on demand.

---

## Architecture

```
INGEST:   S3 ──▶ EventBridge ──▶ Step Functions ──▶ Lambda ──▶ DynamoDB
          (CSV)                   (retry on fail)   (validate)  (store)
                                        │
                                        └── on failure ──▶ SNS ──▶ email alert

DELIVER:  Client ──▶ API Gateway ──▶ Lambda ──▶ DynamoDB
          (GET /prices)              (read)     (query)
```

A CSV file uploaded to S3 triggers EventBridge, which starts a Step Functions workflow. Step Functions calls a Lambda that validates and transforms the data and writes it to DynamoDB, automatically retrying on transient failures. If the workflow ultimately fails, Step Functions publishes an alert to SNS, which emails the team. A separate API Gateway GET endpoint reads the stored data back through a Lambda and returns it as JSON.

---

## What it does

- **Ingests** price data from CSV files dropped into an S3 bucket.
- **Processes** each file with a Lambda that validates the columns and transforms the rows.
- **Stores** the data in DynamoDB, keyed by commodity and date, so re-processing the same file overwrites instead of duplicating (idempotent).
- **Orchestrates** the processing with Step Functions, which retries automatically on failure with exponential backoff.
- **Alerts** the team by email through SNS if the pipeline gives up after all retries.
- **Serves** the data through a REST API (API Gateway + Lambda) that returns the current price list as JSON.

---

## Tech stack

| Concern | AWS service |
|---------|-------------|
| Ingestion / storage | Amazon S3 |
| Eventing | Amazon EventBridge |
| Orchestration & retry | AWS Step Functions |
| Compute | AWS Lambda (Python) |
| Database | Amazon DynamoDB (NoSQL) |
| Alerting | Amazon SNS |
| API delivery | Amazon API Gateway (HTTP API) |
| Language | Python (boto3) |

---

## Key design decisions

- **Event-driven** — the pipeline starts automatically when a file arrives. No schedules, no polling.
- **Serverless** — no servers to manage or patch; everything scales to zero when idle and scales up automatically under load.
- **Idempotent writes** — DynamoDB items are keyed by commodity + date, so re-processing a file overwrites rather than duplicating. Re-running is always safe.
- **Retry with backoff** — Step Functions retries the processing step up to three times with growing delays (2s, 4s, 8s), so transient errors recover on their own.
- **Fail loud, not silent** — if all retries fail, an SNS alert is sent, so failures surface instead of disappearing.
- **Separation of read and write** — the write path (ingestion) and the read path (API) are independent, each with its own least-privilege Lambda.

---

## How the pieces connect

1. A CSV is uploaded to the S3 bucket.
2. S3 emits an event to EventBridge (the bucket has EventBridge notifications enabled).
3. An EventBridge rule matches "object created" events and starts the Step Functions state machine.
4. Step Functions invokes the processing Lambda, with a retry policy.
5. The Lambda reads the CSV from S3, validates it, and writes the rows to DynamoDB.
6. If the Lambda keeps failing, Step Functions catches the error and publishes to SNS, which emails an alert.
7. Separately, a client calls `GET /prices` on API Gateway, which invokes a read Lambda that scans DynamoDB and returns the data as JSON.

---

## Problems solved while building it

This was built and debugged hands-on. A few issues worth noting:

- **Lambda code not deployed** — data wasn't appearing in DynamoDB because the function had been edited but not deployed, so the old version was still running. A reminder that editing isn't shipping.
- **URL-encoded S3 keys** — object keys arrive URL-encoded in the event (spaces become `+`), so the key has to be decoded before reading the file, or the lookup fails.
- **Event structure mismatch** — the Lambda first failed with a `KeyError`; inspecting the full event payload showed the exact shape (`detail.bucket.name`) and fixed it. The lesson: read the real event before changing code.
- **IAM permissions** — each Lambda needs explicit permission for the services it touches (S3 read, DynamoDB read/write), following least privilege.

The failure path was tested deliberately by pointing the Lambda at a wrong resource — the retries ran, the workflow failed, and the SNS alert email arrived as expected.

---

## What I learned

This project tied together the core building blocks of a serverless data platform: event-driven ingestion, orchestration, a NoSQL store, API delivery, and reliability through retries and alerting. The most valuable part was debugging it end-to-end on real infrastructure — permissions, event shapes, and deployment steps are the things that actually break, and working through them is how the pieces start to make sense as a whole.
