"""
weather-fetcher Lambda
Gọi OpenWeatherMap API cho danh sách thành phố, ghi kết quả vào DynamoDB.
Trigger: EventBridge schedule (vd: rate(30 minutes))

Environment variables:
  OWM_API_KEY  - API key của OpenWeatherMap
  TABLE_NAME   - tên bảng DynamoDB (vd: WeatherData)
  CITIES       - danh sách thành phố cách nhau bởi dấu phẩy (vd: "Hanoi,Ho Chi Minh City,Da Nang")
"""

import json
import os
import time
import urllib.request
import urllib.parse
import sys
from decimal import Decimal

# Đảm bảo UTF-8 cho Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Mặc định cấu hình
DEFAULT_API_KEY = "e6bf3b2aa25e42d37925a5eb03e80390"
DEFAULT_TABLE = "WeatherData"
DEFAULT_CITIES = "Hanoi,Ho Chi Minh City,Da Nang,Hue,Nha Trang,Da Lat,Haiphong,Can Tho,Tokyo,London"

OWM_API_KEY = os.environ.get("OWM_API_KEY", DEFAULT_API_KEY)
TABLE_NAME = os.environ.get("TABLE_NAME", DEFAULT_TABLE)
CITIES_RAW = os.environ.get("CITIES", DEFAULT_CITIES)
CITIES = [c.strip() for c in CITIES_RAW.split(",") if c.strip()]

OWM_URL = "https://api.openweathermap.org/data/2.5/weather"


def fetch_weather(city):
    params = {
        "q": city,
        "appid": OWM_API_KEY,
        "units": "metric",
        "lang": "vi",
    }
    url = f"{OWM_URL}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "WeatherFetcher/1.0"})
    with urllib.request.urlopen(req, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"), parse_float=Decimal)


def handler(event, context):
    import boto3
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(TABLE_NAME)
    results = []
    errors = []
    current_time = int(time.time())
    ttl_timestamp = current_time + (30 * 24 * 3600)  # TTL: Tự động xóa sau 30 ngày

    for city in CITIES:
        try:
            data = fetch_weather(city)
            item = {
                "city": city,
                "timestamp": current_time,
                "ttl": ttl_timestamp,
                "temperature": data["main"]["temp"],
                "feels_like": data["main"]["feels_like"],
                "humidity": int(data["main"]["humidity"]),
                "pressure": int(data["main"]["pressure"]),
                "wind_speed": data["wind"]["speed"],
                "description": data["weather"][0]["description"],
                "icon": data["weather"][0]["icon"],
            }
            table.put_item(Item=item)
            # Chuyển Decimal sang float để serialize JSON trong return response
            item_json = dict(item)
            item_json["temperature"] = float(item["temperature"])
            item_json["feels_like"] = float(item["feels_like"])
            item_json["wind_speed"] = float(item["wind_speed"])
            results.append(item_json)
        except Exception as e:
            print(f"Error fetching {city}: {e}")
            errors.append({"city": city, "error": str(e)})

    print(f"Fetched {len(results)} cities, {len(errors)} errors")
    return {
        "statusCode": 200,
        "body": json.dumps(
            {"fetched": len(results), "errors": errors}, ensure_ascii=False
        ),
    }


if __name__ == "__main__":
    print("=== TEST LOCAL: FETCHING LIVE WEATHER DATA ===")
    for city in CITIES:
        try:
            res = fetch_weather(city)
            print(f"✅ [{city}]: {res['main']['temp']}°C | Cảm giác: {res['main']['feels_like']}°C | Độ ẩm: {res['main']['humidity']}% | {res['weather'][0]['description']}")
        except Exception as err:
            print(f"❌ [{city}] Error: {err}")
