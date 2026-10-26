
## Identify Stock Symbol using supported exchange code

import os
import sys

import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("FINNHUB_API_KEY")
EXCHANGE_CODE = os.getenv("FINNHUB_EXCHANGE_CODE", "").strip()

if not API_KEY or API_KEY == "replace_with_your_token":
    sys.exit("ERROR: Set your real FINNHUB_API_KEY in .env.")

if not EXCHANGE_CODE:
    sys.exit("ERROR: Set FINNHUB_EXCHANGE_CODE in .env.")

url = "https://finnhub.io/api/v1/stock/symbol"
params = {
    "exchange": EXCHANGE_CODE,
    "token": API_KEY,
}

try:
    response = requests.get(url, params=params, timeout=20)

    print(f"HTTP status: {response.status_code}")
    response.raise_for_status()

    try:
        payload = response.json()
    except ValueError:
        sys.exit("ERROR: Finnhub returned a non-JSON response.")

    if isinstance(payload, dict):
        # Do not print the request URL or API token.
        message = payload.get("error", "Unexpected response object")
        sys.exit(f"ERROR: Finnhub returned an error: {message}")

    if not isinstance(payload, list):
        sys.exit("ERROR: Unexpected response format.")

    print(f"Exchange code: {EXCHANGE_CODE}")
    print(f"Records returned: {len(payload)}")

    if not payload:
        print("WARNING: Request succeeded, but no symbols were returned.")
    else:
        print("First three records:")
        for item in payload[:3]:
            print({
                "symbol": item.get("symbol"),
                "description": item.get("description"),
                "type": item.get("type"),
                "currency": item.get("currency"),
            })

        print("API smoke test completed.")

except requests.HTTPError:
    # Avoid printing the prepared request, which may contain the token.
    status = response.status_code
    print(f"HTTP error: {status}")

    if status == 401:
        print("Check the API key and authentication.")
    elif status == 403:
        print("Check API permissions or plan restrictions.")
    elif status == 429:
        print("Rate limit reached. Check your plan and usage.")
    else:
        print("Check Finnhub's response and API documentation.")

    sys.exit(1)

except requests.RequestException as exc:
    # Avoid printing request URLs or request objects.
    print(f"Network/request error: {type(exc).__name__}")
    sys.exit(1)
