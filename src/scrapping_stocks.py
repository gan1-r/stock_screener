import requests
import pandas as pd


def scrapping_etf(page, type='stock'):

    base_url_stock = "https://pluang.com/_next/data/dashboard_x4atPVY89e/id/explore/us-market/stocks.json"
    base_url_etf = "https://pluang.com/_next/data/dashboard_x4atPVY89e/id/explore/us-market/etf.json"
    if type == 'stock':
        base_url = base_url_stock
    elif type == 'etf':
        base_url = base_url_etf
    else:
        print('type unknown')
        return False


    params = {
        "assetType": "us-market",
        "subAssetType": "etf",
        "page": page
    }

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json"
    }

    r = requests.get(base_url, params=params, headers=headers)
    response_json = r.json()

    rows = []
    data = response_json["pageProps"]["data"]

    for cat in data["assetCategories"]:
        for sub in cat["assetCategoryData"]:
            for asset in sub["assets"]:
                t = asset["tileInfo"]

                rows.append({
                    "symbol": t.get("displaySymbol"),
                    "name": t.get("name"),
                    "asset_id": t.get("assetId"),
                })

    df = pd.DataFrame(rows)
    return df


all_stock = pd.DataFrame()
count = 1
while True:
    try:
       _df =  scrapping_etf(page=count)
       print(f'{count} [OK]')
       print(_df)
    except Exception as e:
        print(e)
    all_stock = pd.concat([all_stock, _df])
    count = count + 1

    if count == 100:
        break

all_stock.to_csv('../data/raw/all_stock.csv', index=False)