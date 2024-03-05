import time
import config 
import ccxt
import pandas as pd
import pytz
from datetime import datetime
import matplotlib.pyplot as plt

symbol = 'SOLUSDT'

bybit = ccxt.bybit({
    'enableRateLimit': True,
    'apiKey': config.api_key,
    'secret': config.api_secret,
    'options': {
        'accountsByType': 'future',
        'adjustForTimeDifference': True
    },
})

POE = 35

# [SETUP] -----------------------------------------------------------

bybit.load_time_difference()

def get_bid_ask():
    pairOrderBook = bybit.fetch_order_book(symbol)
    pair_bid = pairOrderBook['bids'][0][0]
    pair_ask = pairOrderBook['bids'][0][0]
    print("The best bid: " + str(pair_bid) + "   The best ask: " + str(pair_ask))
    return pair_bid, pair_ask

def get_market_price():
    ticker = bybit.fetch_ticker(symbol)
    market_price = ticker['last']
    return market_price

def fetch_data(timeframe, length=500):
    bars = bybit.fetch_ohlcv(symbol, timeframe=timeframe, limit=length)
    df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

    df['timestamp'] = df['timestamp'].dt.tz_localize(pytz.utc).dt.tz_convert(pytz.timezone('Australia/Sydney'))

    return df

def buy_order(leverage, POE, SLper, TPper):
    pos_size = ((POE / 100) * equity) / get_market_price() * leverage
    takeProfit = get_market_price() * TPper
    stopLoss = get_market_price() * SLper
    params = {
        'stopLoss': {
        'type': 'limit',  # or 'market', this field is not necessary if limit price is specified
        'price': stopLoss + ((get_market_price() - stopLoss) * 0.1),  # limit price for a limit stop loss order
        'triggerPrice': stopLoss,
        },
        'takeProfit': {
        'type': 'market',  # or 'limit', this field is not necessary if limit price is specified
        # no limit price for a market take profit order
        # 'price': 160.33,  # this field is not necessary for a market take profit order
        'triggerPrice': takeProfit,
        }
    }

    bybit.create_market_buy_order(symbol, pos_size, params)
    print("Congratulations! You made a buy order!")  

def sell_order(leverage, POE, SLper, TPper):
    pos_size = ((POE / 100) * equity) / get_market_price() * leverage
    takeProfit = get_market_price() * 1 - (TPper - 1)
    stopLoss = get_market_price() * 1 + (1 - SLper)
    params = {
        'stopLoss': {
        'type': 'limit',  # or 'market', this field is not necessary if limit price is specified
        'price': stopLoss + ((get_market_price() - stopLoss) * 0.1),  # limit price for a limit stop loss order
        'triggerPrice': stopLoss,
        },
        'takeProfit': {
        'type': 'market',  # or 'limit', this field is not necessary if limit price is specified
        # no limit price for a market take profit order
        # 'price': 160.33,  # this field is not necessary for a market take profit order
        'triggerPrice': takeProfit,
        }
    }

    bybit.create_market_sell_order(symbol, pos_size, params)
    print("Congratulations! You made a sell order!")  

def candleProfit():
    data15m = fetch_data("15m")
    if data15m['open'].iloc[-1] < get_market_price():
        return True
    else:
        return False

equity = bybit.fetch_balance()['total']['USDT']
print("Total equity: " + str(equity))

data15m = fetch_data("15m")

# [VOLUME] -----------------------------------------------------------

dataSpikeThreshold = 100000

def isVolumeSpiking():
    data15m = fetch_data("15m")
    data15m["volume_change"] = data15m["volume"].diff()
    current_volume_change = data15m['volume_change'].iloc[-1]  # Volume change for the current bar
    
    if current_volume_change > dataSpikeThreshold:  #this only checks if volume is spiking up, if you want to check if its spiking up or down, using abs(current_volume_change)
        return True
    else:
        return False

def volumeMASpike():
    data15m = fetch_data("15m")
    data15m['volume_ma'] = data15m['volume'].rolling(window=20).mean()
    current_volume = data15m["volume"].iloc[-1]
    current_MA = data15m['volume_ma'].iloc[-1]

    if current_volume > current_MA:
        return True
    else:
        return False


# [EMA and SMA] ------------------------------------------------------

def fetch_sma(length):
    data15m = fetch_data("15m")
    data15m[f"{length}_sma"] = data15m["close"].rolling(window=length).mean()

    return data15m[f"{length}_sma"]

def fetch_ema(length):
    data15m = fetch_data("15m")
    ema = data15m["close"].ewm(span=length, adjust=False).mean()
    data15m[f"{length}_ema"] = ema

    return data15m[f"{length}_ema"]

# [Long Conditions for moving averages]

def maLong1():
    if fetch_ema(6).iloc[-1] > fetch_sma(18).iloc[-1] and fetch_ema(6).iloc[-2] < fetch_sma(20).iloc[-2]:
        return True
    else:
        return False

def maLong2():
    if fetch_ema(3).iloc[-1] > fetch_ema(9).iloc[-1] and fetch_ema(3).iloc[-2] < fetch_ema(9).iloc[-2]:
        return True
    else:
        return False

def maLong3():
    if fetch_ema(3).iloc[-1] > fetch_ema(6).iloc[-1] and fetch_ema(3).iloc[-2] < fetch_ema(6).iloc[-2]:
        return True
    else:
        return False

# [Short Conditions for moving averages]

def maShort1():
    if fetch_ema(6).iloc[-1] < fetch_sma(18).iloc[-1] and fetch_ema(6).iloc[-2] > fetch_sma(20).iloc[-2]:
        return True
    else:
        return False

def maShort2():
    if fetch_ema(3).iloc[-1] < fetch_ema(9).iloc[-1] and fetch_ema(3).iloc[-2] > fetch_ema(9).iloc[-2]:
        return True
    else:
        return False

def maShort3():
    if fetch_ema(3).iloc[-1] < fetch_ema(6).iloc[-1] and fetch_ema(3).iloc[-2] > fetch_ema(6).iloc[-2]:
        return True
    else:
        return False


# [SUPPORT AND RESISTANCE] -------------------------------------------

def is_support(i):
    data15m = fetch_data("15m", 200)
    if data15m["low"].iloc[i] > data15m["low"].iloc[i-1]:
        return False

    if data15m["low"].iloc[i-1] > data15m["low"].iloc[i-2]:
        return False

    if data15m["low"].iloc[i] > data15m["low"].iloc[i+1]:
        return False
    
    if data15m["low"].iloc[i+1] > data15m["low"].iloc[i-2]:
        return False
    
    return True


def is_resistance(i):
    data15m = fetch_data("15m", 200)
    if data15m["high"].iloc[i] < data15m["high"].iloc[i-1]:
        return False

    if data15m["high"].iloc[i-1] < data15m["high"].iloc[i-2]:
        return False

    if data15m["high"].iloc[i] < data15m["high"].iloc[i+1]:
        return False
    
    if data15m["high"].iloc[i+1] < data15m["high"].iloc[i-2]:
        return False
    
    return True


def filterResistance(arr, range_size = 5):  # DONT CALL THIS DIRECTLY, IT IS ALREDAY CALLED THROUGH OTHER FUCNTIONS
    result = []
    current_group = [arr[0]]

    for number in arr[1:]:
        if abs(number - current_group[-1]) <= range_size:
            current_group.append(number)
        else:
            average = sum(current_group) / len(current_group)
            result.append(average)

            current_group = [number]
    
    average = sum(current_group) / len(current_group)
    result.append(average)

    return result


def findSRLevels():  #DONT CALL THIS DIRECTLY, IT IS CALELD THROUGH OTHER FUNCTION
    data15m = fetch_data("15m", 200)
    SRLevels = []
    for row in range(2, 200-2):
        if is_support(row):  # 1 means support, 2 means resistance
            SRLevels.append(data15m["high"].iloc[row])
        if is_resistance(row):  # 1 means support, 2 means resistance
            SRLevels.append(data15m["low"].iloc[row])

    SRLevels = filterResistance(SRLevels, 0.6)
    return SRLevels


def isNearKeyLevel(threshold = 0.042):  # THIS FUNCTION CALLS ALL THE OTHER FUNCTIONS, JSUT CALL THIS AND THE IS SUPPORT FUCNTION
    data15m = fetch_data("15m")
    SRLevels = findSRLevels()
    for i in SRLevels:
        if abs(data15m["close"].iloc[-1] - i) < threshold:
            return i

    return False


def isSupport(price, length=6): # CALL THIS AS WELL
    data15m = fetch_data("15m", length)
    average = 0
    for row in range(0, length):
        average += data15m["close"].iloc[row]
    average = average/length
    print(average)
    if average >= price:
        return True
    else:
        return False
    
def get_confidence():
    confidence = 0
    confidenceSpecifics = []
    if maLong1():
        confidence += 1
        confidenceSpecifics.append("maLong1")
    if maLong2():
        confidence += 1
        confidenceSpecifics.append("maLong2")
    if maLong3():
        confidence += 1
        confidenceSpecifics.append("maLong3")
    if maShort1():
        confidence -= 1
        confidenceSpecifics.append("maShort1")
    if maShort2():
        confidence -= 1
        confidenceSpecifics.append("maShort2")
    if maShort3():
        confidence -= 1
        confidenceSpecifics.append("maShort3")
    if isNearKeyLevel() != False:
        keyLevel = isNearKeyLevel()
        if isSupport(keyLevel):
            confidence += 0.5
            confidenceSpecifics.append(f"hitting support {keyLevel}")
        else:
            confidence -= 0.5
            confidenceSpecifics.append(f"hitting resistance {keyLevel}")
    return confidence, confidenceSpecifics

def calculateBuyStopLoss():
    stopLoss = None
    SRLevels = findSRLevels()
    for i in SRLevels:
        if i < get_market_price() and (stopLoss is None or get_market_price()  - i < get_market_price() - stopLoss):
            stopLoss = i

    percentageStopLoss = stopLoss / get_market_price()
    return percentageStopLoss


def calculateSellStopLoss():
    stopLoss = None
    SRLevels = findSRLevels()
    for i in SRLevels:
        if i > get_market_price() and (stopLoss is None or i - get_market_price() < stopLoss - get_market_price()):
            stopLoss = i

    percentageStopLoss = stopLoss / get_market_price()
    return percentageStopLoss

while True:
    data15m = fetch_data("15m")
    bybit.load_time_difference()
    open_positions = bybit.fetch_open_orders(symbol)
    first, last = get_confidence()

    if(not open_positions):
        if first > 1:
            buy_order(30, 15, calculateBuyStopLoss(), 1.05)
            print("You made a buy order! Good job" + "  " + str(datetime.now()) + "  " + str(last))
        elif first < -1:
            sell_order(30, 15, calculateSellStopLoss(), 1.05)	
            print("You made a sell order! Good job" + "  " + str(datetime.now()) + "  " + str(last))
        else:
            print("Was not confident enough" + "  " + str(datetime.now()))
    else:
        print("You weren't even close :(" + "  " + str(datetime.now()))

    time.sleep(200)


