"""
weather-api-handler Lambda
Đọc dữ liệu mới nhất (và lịch sử gần đây) từ DynamoDB, trả về JSON cho dashboard.
Trigger: API Gateway HTTP API - GET /weather?city=Hanoi&limit=24

Environment variables:
  TABLE_NAME - tên bảng DynamoDB (vd: WeatherData)
"""

import json
import os
import sys

# Đảm bảo UTF-8 cho Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from decimal import Decimal


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            if obj % 1 == 0:
                return int(obj)
            return float(obj)
        return super(DecimalEncoder, self).default(obj)


TABLE_NAME = os.environ.get("TABLE_NAME", "WeatherData")

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET",
    "Access-Control-Allow-Headers": "*",
    "Content-Type": "application/json",
}


def handler(event, context):
    import boto3
    from boto3.dynamodb.conditions import Key

    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(TABLE_NAME)

    query_params = (event or {}).get("queryStringParameters") or {}
    city = query_params.get("city", "Hanoi")
    limit = int(query_params.get("limit", 24))

    try:
        response = table.query(
            KeyConditionExpression=Key("city").eq(city),
            ScanIndexForward=False,  # mới nhất trước
            Limit=limit,
        )
        items = response.get("Items", [])
        # Trả về theo thứ tự thời gian tăng dần để dễ vẽ biểu đồ
        items.sort(key=lambda x: int(x["timestamp"]))

        return {
            "statusCode": 200,
            "headers": CORS_HEADERS,
            "body": json.dumps(
                {"city": city, "data": items},
                cls=DecimalEncoder,
                ensure_ascii=False,
            ),
        }
    except Exception as e:
        print(f"Error querying DynamoDB: {e}")
        return {
            "statusCode": 500,
            "headers": CORS_HEADERS,
            "body": json.dumps({"error": str(e)}, ensure_ascii=False),
        }


if __name__ == "__main__":
    print("=== TEST LOCAL: API HANDLER EVENT MOCK ===")
    mock_event = {"queryStringParameters": {"city": "Hanoi", "limit": "10"}}
    print(f"Mock Event: {mock_event}")
    print("Code handler đã sẵn sàng để nhận request từ API Gateway HTTP API GET /weather.")
