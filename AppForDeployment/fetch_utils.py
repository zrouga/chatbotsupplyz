import requests
import pandas as pd


def get_user_token(user_id: str) -> str:
    url = f"https://gateway-dev.supplyz.tech/user_management_service/ai/v1/auth?user_id={user_id}&duration=72h"
    headers = {"ai-key": "randomAIKey"}
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    return resp.json()["token"]


def fetch_data(table_name: str, token: str) -> pd.DataFrame:
    if table_name == "clients":
        url = "https://gateway-dev.supplyz.tech/orders_service/ai/v1/clients"
    elif table_name == "invoices":
        url = "https://gateway-dev.supplyz.tech/orders_service/ai/v1/invoices"
    elif table_name == "items":
        url = "https://gateway-dev.supplyz.tech/inventory/ai/v1/items"
    elif table_name == "purchases":
        url = "https://gateway-dev.supplyz.tech/inventory/ai/v1/purchases"
    elif table_name == "suppliers":
        url = "https://gateway-dev.supplyz.tech/inventory/ai/v1/suppliers"
    else:
        raise ValueError(f"Unknown table: {table_name}")

    headers = {"ai-key": "randomAIKey", "user-token": token}
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    json_data = resp.json()

    if isinstance(json_data, dict) and "data" in json_data:
        items_list = json_data["data"]
    elif isinstance(json_data, list):
        items_list = json_data
    else:
        items_list = []

    return pd.DataFrame(items_list)
