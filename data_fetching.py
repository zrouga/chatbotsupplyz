import requests
import pandas as pd
import streamlit as st

TABLE_URLS = {
    "clients": "https://gateway-dev.supplyz.tech/orders_service/ai/v1/clients",
    "invoices": "https://gateway-dev.supplyz.tech/orders_service/ai/v1/invoices",
    "items": "https://gateway-dev.supplyz.tech/inventory/ai/v1/items",
    "purchases": "https://gateway-dev.supplyz.tech/inventory/ai/v1/purchases",
    "suppliers": "https://gateway-dev.supplyz.tech/inventory/ai/v1/suppliers",
}


def get_user_token(user_id: str) -> str:
    url = f"https://gateway-dev.supplyz.tech/user_management_service/ai/v1/auth?user_id={user_id}&duration=72h"
    headers = {"ai-key": "randomAIKey"}
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    return resp.json()["token"]


def flatten_json(y, sep="_"):
    """
    Recursively flattens a nested JSON/dictionary.
    - For dictionaries, it concatenates keys using the given separator.
    - For lists, if all elements are dicts, it flattens each and adds an index.
      Otherwise, it keeps the list as is.
    """
    out = {}

    def flatten(x, name=""):
        if isinstance(x, dict):
            for k, v in x.items():
                flatten(v, f"{name}{k}{sep}")
        elif isinstance(x, list):
            # If the list elements are dictionaries, flatten each with an index
            if x and all(isinstance(item, dict) for item in x):
                for i, item in enumerate(x):
                    flatten(item, f"{name}{i}{sep}")
            else:
                # Otherwise, store the list as a whole
                out[name[:-1]] = x
        else:
            out[name[:-1]] = x

    flatten(y)

    return out


def fetch_data(table_name: str) -> pd.DataFrame:
    token = get_user_token("670175884b923eac46d240f3")
    try:
        url = TABLE_URLS[table_name]
    except KeyError:
        raise ValueError(f"Unknown table: {table_name}")
    headers = {"ai-key": "randomAIKey", "user-token": token}
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    json_data = resp.json()

    flat_records = [flatten_json(record) for record in json_data["data"]]
    df = pd.DataFrame(flat_records)
    return df.dropna(axis=1, how="all")


def update_data():
    fetch_data("items").to_csv(
        "data/items.csv"
    )
    fetch_data("clients").to_csv(
        "data/clients.csv"
    )
    fetch_data("purchases").to_csv(
        "data/purchases.csv"
    )
    fetch_data("invoices").to_csv(
        "data/invoices.csv"
    )
    fetch_data("suppliers").to_csv(
        "data/suppliers.csv"
    )


st.cache_data


def get_data():
    items = pd.read_csv("data/items.csv")
    clients = pd.read_csv(
        "data/clients.csv"
    )
    purchases = pd.read_csv(
        "data/purchases.csv"
    )
    invoices = pd.read_csv(
        "data/invoices.csv"
    )
    suppliers = pd.read_csv(
        "data/suppliers.csv"
    )
    items_sig = items.dtypes.to_dict()
    clients_sig = clients.dtypes.to_dict()
    purchases_sig = purchases.dtypes.to_dict()
    invoices_sig = invoices.dtypes.to_dict()
    suppliers_sig = suppliers.dtypes.to_dict()

    return {
        "items": [items, items_sig],
        "clients": [clients, clients_sig],
        "purchases": [purchases, purchases_sig],
        "invoices": [invoices, invoices_sig],
        "suppliers": [suppliers, suppliers_sig],
    }
