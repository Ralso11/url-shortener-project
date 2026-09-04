import json
import os
import secrets
import string
import boto3

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["TABLE_NAME"])


def generate_short_code(length=6):
    characters = string.ascii_letters + string.digits
    return "".join(secrets.choice(characters) for _ in range(length))


def handler(event, context):
    method = event["requestContext"]["http"]["method"]

    if method == "POST":
        return shorten_url(event)

    if method == "GET":
        return redirect_to_url(event)

    return {
        "statusCode": 405,
        "body": json.dumps({"error": "Method not allowed"})
    }


def shorten_url(event):
    body = json.loads(event.get("body") or "{}")
    original_url = body.get("url")

    if not original_url:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Missing 'url' in request body"})
        }

    short_code = generate_short_code()

    table.put_item(Item={
        "id": short_code,
        "original_url": original_url
    })

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({
            "short_code": short_code,
            "original_url": original_url
        })
    }


def redirect_to_url(event):
    short_code = event["pathParameters"]["code"]

    response = table.get_item(Key={"id": short_code})
    item = response.get("Item")

    if not item:
        return {
            "statusCode": 404,
            "body": json.dumps({"error": "Short code not found"})
        }

    return {
        "statusCode": 302,
        "headers": {"Location": item["original_url"]}
    }
