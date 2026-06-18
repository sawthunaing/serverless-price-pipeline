import boto3
import json
from decimal import Decimal

table = boto3.resource("dynamodb").Table("prices")

def lambda_handler(event, context):
    result = table.scan()
    items = result.get("Items", [])

    # DynamoDB returns Decimal; convert so JSON can serialise
    for item in items:
        for k, v in item.items():
            if isinstance(v, Decimal):
                item[k] = float(v)

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(items),
    }