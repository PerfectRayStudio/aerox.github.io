import hashlib
import hmac
import json
import time
from flask import Flask, request
import requests
app = Flask(__name__)

# ---------------------------------API AND ACCOUNT SETTINGS----------------------------------------
API_KEY = '5gy9Z7MWDqJ8XPUCc6YEOxqvfDnNKCjo0gBDmWztmwsPerKPZ5RWjYF6lzV9AECQDS0JPgC0PJUdUcpDGT3Q'
API_SECRET = '239uKwz9las3pFtnDouK11LjzzwTMaC2BO0wCELKyNxO9bn2E7YHJgoewmmbSpzfFKlX7RasndeJJJ7tzZQ'
BASE_URL = 'https://open-api-vst.bingx.com'  # Замените на URL API BingX

USDT_DEPOSIT = 150
RISK_PERCENTAGE = 3
ALLOWS_PAIRS = {"BTC-USDT", "ETH-USDT", "DOGE-USDT"}
LEVERAGE_SETTINGS = {
    "BTC-USDT": 75,
    "ETH-USDT": 75,
    "DOGE-USDT": 50,
}
TAKE_PROFITS = {
    "BTC-USDT": [0.01, 0.02, 0.03, 0.05],
    "ETH-USDT": [0.01, 0.02, 0.03, 0.05],
    "DOGE-USDT": [0.03, 0.05, 0.10, 0.15]
}
STOP_PROFITS = {
    "BTC-USDT": 0.025,
    "ETH-USDT": 0.025,
    "DOGE-USDT": 0.035
}
# -------------------------------------------------------------------------------------------------
def open_position(symbol, positiion):
    leverage = LEVERAGE_SETTINGS[symbol]
    if positiion == "LONG":
        #set_cross_margin("APT-USDT")
        change_leverage(symbol, leverage, "LONG")
        path = '/openApi/swap/v2/trade/order'
        method = "POST"
        paramsMap = {
            "symbol": symbol,
            "side": "BUY",
            "positionSide": "LONG",
            "type": "MARKET",
            "quantity": calc_margin(symbol),
        }
        paramsStr = parseParam(paramsMap)
        return send_request(method, path, paramsStr, {})
    if positiion == "SHORT":
        leverage = LEVERAGE_SETTINGS[symbol]
        change_leverage(symbol, leverage, "SHORT")
        path = '/openApi/swap/v2/trade/order'
        method = "POST"
        paramsMap = {
            "symbol": symbol,
            "side": "SELL",
            "positionSide": "SHORT",
            "type": "MARKET",
            "quantity": calc_margin(symbol),
        }
        paramsStr = parseParam(paramsMap)
        return send_request(method, path, paramsStr, {})

#------------------------------------------------UTILS---------------------------------------------
def set_take_profits(symbol, position):
    entry_price = get_market_price(symbol)
    piece_of_cake = float(calc_margin(symbol) / 4)
    if position == "LONG":
        for profit in TAKE_PROFITS[symbol]:
            stop_price = float(entry_price * (1 + profit))
            paramsMap = {
                "symbol": symbol,
                'side': 'BUY',
                'positionSide': 'LONG',
                "type": "TAKE_PROFIT_MARKET",
                "stopPrice": stop_price,
                "quantity": piece_of_cake,
            }
            paramsStr = parseParam(paramsMap)
            path = '/openApi/swap/v2/trade/order'
            method = "POST"
            response = send_request(method, path, paramsStr, {})
            print(f"[LONG TakeProfiter]Order for {symbol} at stop price {stop_price}:{response}")
    if position == "SHORT":
        for profit in TAKE_PROFITS[symbol]:
            stop_price = float(entry_price * (1 - profit))
            paramsMap = {
                "symbol": symbol,
                'side': 'SELL',
                'positionSide': 'SHORT',
                "type": "TAKE_PROFIT_MARKET",
                "stopPrice": stop_price,
                "quantity": piece_of_cake,
            }
            paramsStr = parseParam(paramsMap)
            path = '/openApi/swap/v2/trade/order'
            method = "POST"
            response = send_request(method, path, paramsStr, {})
            print(f"[SHORT TakeProfiter] Order for {symbol} at stop price {stop_price}:{response}")

def set_stop_loss(symbol, position):
    if position == "LONG":
        stop_loss = STOP_PROFITS.get(symbol, 1)
        entry_price = get_market_price(symbol)
        stop_price = float(entry_price * (1 - stop_loss))
        paramsMap = {
            "symbol": symbol,
            'side': 'BUY',
            'positionSide': 'LONG',
            "type": "STOP_MARKET",
            "stopPrice": stop_price,
            "quantity": calc_margin(symbol),
        }
        paramsStr = parseParam(paramsMap)
        payload = {}
        path = '/openApi/swap/v2/trade/order'
        method = "POST"
        response = send_request(method, path, paramsStr, payload)
        print(f"[LONG StopLosser] Order for {symbol} at stop price {stop_price}:{response}")
    if position == "SHORT":
        stop_loss = STOP_PROFITS.get(symbol, 1)
        entry_price = get_market_price(symbol)
        stop_price = float(entry_price * (1 + stop_loss))
        paramsMap = {
            "symbol": symbol,
            'side': 'SELL',
            'positionSide': 'SHORT',
            "type": "STOP_MARKET",
            "stopPrice": stop_price,
            "quantity": calc_margin(symbol),
        }
        paramsStr = parseParam(paramsMap)
        payload = {}
        path = '/openApi/swap/v2/trade/order'
        method = "POST"
        response = send_request(method, path, paramsStr, payload)
        print(f"[LONG StopLosser] Order for {symbol} at stop price {stop_price}:{response}")

# Генерация quantity на сделку (риск позиции)
def set_cross_margin(symbol):
    payload = {}
    path = '/openApi/swap/v2/trade/marginType'
    method = "POST"
    paramsMap = {
        "symbol": symbol,
        "marginType": "CROSSED",
        "recvWindow": "60000",
    }
    paramsStr = parseParam(paramsMap)
    return send_request(method, path, paramsStr, payload)
def calc_margin(symbol):
    current_price = get_market_price(symbol)
    margin = USDT_DEPOSIT * (RISK_PERCENTAGE / 100)
    leverage = LEVERAGE_SETTINGS.get(symbol, 1)
    effective_margin = margin * leverage
    quantity = effective_margin / current_price
    return quantity
def change_leverage(symbol, leverage, side):
    payload = {}
    path = '/openApi/swap/v2/trade/leverage'
    method = "POST"
    paramsMap = {
        "symbol": symbol,
        "side": side,
        "leverage": leverage,
    }
    paramsStr = parseParam(paramsMap)
    return send_request(method, path, paramsStr, payload)

def get_sign(api_secret, payload):
    signature = hmac.new(api_secret.encode("utf-8"), payload.encode("utf-8"), digestmod=hashlib.sha256).hexdigest()
    print("sign=" + signature)
    return signature

def send_request(method, path, urlpa, payload):
    url = "%s%s?%s&signature=%s" % (BASE_URL, path, urlpa, get_sign(API_SECRET, urlpa))
    print(url)
    headers = {
        'X-BX-APIKEY': API_KEY,
    }
    response = requests.request(method, url, headers=headers, data=payload)
    return response.text

def parseParam(paramsMap):
    sortedKeys = sorted(paramsMap)
    paramsStr = "&".join(["%s=%s" % (x, paramsMap[x]) for x in sortedKeys])
    if paramsStr != "":
     return paramsStr+"&timestamp="+str(int(time.time() * 1000))
    else:
     return paramsStr+"timestamp="+str(int(time.time() * 1000))
def get_market_price(symbol):
    price_response = send_request("GET", '/openApi/swap/v2/quote/premiumIndex', parseParam({"symbol": symbol}), {})
    price_data = json.loads(price_response)
    # Предполагаем, что цена находится в price_data['premiumIndex']
    return float(price_data['data']['markPrice'])
open_position("DOGE-USDT", "LONG")
set_take_profits("DOGE-USDT", "LONG")
set_stop_loss("DOGE-USDT", "LONG")
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    print(f"Received data: {data}")
    comment = data.get('comment', '')
    if "Long" in comment:
        symbol = comment.split("_")[2]  # Получаем символ из комментария
        open_position(symbol, "LONG")
        set_take_profits(symbol, "LONG")
        set_stop_loss(symbol, "LONG")
    elif "Short" in comment:
        symbol = comment.split("_")[2]  # Получаем символ из комментария
        open_position(symbol, "SHORT")
        set_take_profits(symbol, "SHORT")
        set_stop_loss(symbol, "SHORT")
    return {"status": "unknown command"}, 400

if __name__ == '__main__':
    app.run(port=5000)