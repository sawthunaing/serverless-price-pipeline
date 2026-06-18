import boto3
import csv
import urllib.parse

s3 = boto3.client("s3")
table = boto3.resource("dynamodb").Table("prices")

def lambda_handler(event, context):
    bucket = event["detail"]["bucket"]["name"]
    key = urllib.parse.unquote_plus(event["detail"]["object"]["key"])
    print(f"New file: s3://{bucket}/{key}")

    obj = s3.get_object(Bucket=bucket, Key=key)
    lines = obj["Body"].read().decode("utf-8").splitlines()
    rows = list(csv.DictReader(lines))

    # Validate required columns
    required = {"date", "commodity", "price"}
    if rows and not required.issubset(rows[0].keys()):
        raise ValueError(f"Missing columns. Found: {list(rows[0].keys())}")

    # Write each row to DynamoDB (upsert — same key overwrites)
    with table.batch_writer() as batch:
        for row in rows:
            batch.put_item(Item={
                "commodity": row["commodity"],
                "date": row["date"],
                "price": str(row["price"]),
            })

    print(f"Wrote {len(rows)} rows to DynamoDB")
    return {"status": "ok", "rows": len(rows)}