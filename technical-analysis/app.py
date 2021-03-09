from ta.momentum import RSIIndicator
from ta.trend import MACD
import os
import numpy as np
import pandas
from ta.volatility import BollingerBands
from unittest import TestCase
import yfinance as yf
from matplotlib import pyplot as plt
import telegram
from flask import Flask, request
import yahoo_fin.stock_info as si
import re

app = Flask(__name__)

TOKEN = 'YOUR BOT API'
bot = telegram.Bot(token=TOKEN)
images_path = "./images"

if not os.path.exists(images_path):
    os.mkdir(images_path)


@app.route('/')
def index():
    return 'wonderful. this works'


@app.route('/setwebhook', methods=['GET', 'POST'])
def set_webhook():
    s = bot.setWebhook('https://<YOUR APP NAME>.herokuapp.com/{HOOK}'.format(HOOK=TOKEN))
    if s:
        return "webhook setup ok"
    else:
        return "webhook setup failed"


@app.route('/{}'.format(TOKEN), methods=['POST'])
def respond():
    # retrieve the message in JSON and then transform it to Telegram object
    update = telegram.Update.de_json(request.get_json(force=True), bot)

    chat_id = update.message.chat.id
    msg_id = update.message.message_id
    # Telegram understands UTF-8, so encode text for unicode compatibility
    text = update.message.text.encode('utf-8').decode()
    # for debugging purposes only
    print("got text message :", text)
    # the first time you chat with the bot AKA the welcoming message
    if text == "/start":
        # print the welcoming message
        bot_welcome = """
        Welcome to Stocks Technical analysis bot.
        The bot sends the technical analysis data of the requested stock symbol.
        """
        # send the welcoming message
        bot.sendMessage(chat_id=chat_id, text=bot_welcome, reply_to_message_id=msg_id)
    else:
        try:
            # clear the message we got from any non alphabets
            text = re.sub(r"\W", "_", text)
            print('getting data for company ' + text.upper())
            indicator = TestTechnicalIndicator()
            indicator.test_tech_indicator(text.upper())

            image = f'images/{text.upper()}_macd.png'
            photo = open(os.path.abspath(image), 'rb')
            bot.sendPhoto(chat_id=chat_id, photo=photo)

            image = f'images/{text.upper()}_rsi.png'
            photo = open(os.path.abspath(image), 'rb')
            bot.sendPhoto(chat_id=chat_id, photo=photo)

            image = f'images/{text.upper()}_bb.png'
            photo = open(os.path.abspath(image), 'rb')
            bot.sendPhoto(chat_id=chat_id, photo=photo)
        except Exception as e:
            print('Exception is ' + str(e))
            # if things went wrong
            bot.sendMessage(chat_id=chat_id, text="There was a problem in the name you used, please enter proper name", reply_to_message_id=msg_id)

    return 'ok'


class Company:
    def __init__(self, symbol):
        self.symbol = symbol
        self.technical_indicators = None
        self.prices = None


def generate_buy_sell_signals(condition_buy, condition_sell, dataframe, strategy):
    last_signal = None
    indicators = []
    buy = []
    sell = []
    for i in range(0, len(dataframe)):
        # if buy condition is true and last signal was not Buy
        if condition_buy(i, dataframe) and last_signal != 'Buy':
            last_signal = 'Buy'
            indicators.append(last_signal)
            buy.append(dataframe['Close'].iloc[i])
            sell.append(np.nan)
        # if sell condition is true and last signal was Buy
        elif condition_sell(i, dataframe)  and last_signal == 'Buy':
            last_signal = 'Sell'
            indicators.append(last_signal)
            buy.append(np.nan)
            sell.append(dataframe['Close'].iloc[i])
        else:
            indicators.append(last_signal)
            buy.append(np.nan)
            sell.append(np.nan)

    dataframe[f'{strategy}_Last_Signal'] = np.array(last_signal)
    dataframe[f'{strategy}_Indicator'] = np.array(indicators)
    dataframe[f'{strategy}_Buy'] = np.array(buy)
    dataframe[f'{strategy}_Sell'] = np.array(sell)



def set_technical_indicators(config, company):
    company.technical_indicators = pandas.DataFrame()
    company.technical_indicators['Close'] = company.prices

    get_macd(config, company)
    get_rsi(config, company)
    get_bollinger_bands(config, company)


def get_macd(config, company):
    close_prices = company.prices
    dataframe = company.technical_indicators
    window_slow = 26
    signal = 9
    window_fast = 12
    macd = MACD(company.prices, window_slow, window_fast, signal)
    dataframe['MACD'] = macd.macd()
    dataframe['MACD_Histogram'] = macd.macd_diff()
    dataframe['MACD_Signal'] = macd.macd_signal()

    generate_buy_sell_signals(
        lambda x, dataframe: dataframe['MACD'].values[x] < dataframe['MACD_Signal'].iloc[x],
        lambda x, dataframe: dataframe['MACD'].values[x] > dataframe['MACD_Signal'].iloc[x],
        dataframe,
        'MACD')
    return dataframe


def get_rsi(config, company):
    close_prices = company.prices
    dataframe = company.technical_indicators
    rsi_time_period = 20

    rsi_indicator = RSIIndicator(close_prices, rsi_time_period)
    dataframe['RSI'] = rsi_indicator.rsi()

    low_rsi = 40
    high_rsi = 70

    generate_buy_sell_signals(
        lambda x, dataframe: dataframe['RSI'].values[x] < low_rsi,
        lambda x, dataframe: dataframe['RSI'].values[x] > high_rsi,
        dataframe, 'RSI')

    return dataframe


def get_bollinger_bands(config, company):

    close_prices = company.prices
    dataframe = company.technical_indicators

    window = 20

    indicator_bb = BollingerBands(close=close_prices, window=window, window_dev=2)

    # Add Bollinger Bands features
    dataframe['Bollinger_Bands_Middle'] = indicator_bb.bollinger_mavg()
    dataframe['Bollinger_Bands_Upper'] = indicator_bb.bollinger_hband()
    dataframe['Bollinger_Bands_Lower'] = indicator_bb.bollinger_lband()

    generate_buy_sell_signals(
        lambda x, signal: signal['Close'].values[x] < signal['Bollinger_Bands_Lower'].values[x],
        lambda x, signal: signal['Close'].values[x] > signal['Bollinger_Bands_Upper'].values[x],
        dataframe, 'Bollinger_Bands')

    return dataframe


class TechnicalIndicatorsChartPlotter:
    def plot_price_and_signals(self, fig, company, data, strategy, axs):
        last_signal_val = data[f'{strategy}_Last_Signal'].values[-1]
        last_signal = 'Unknown' if not last_signal_val else last_signal_val
        title = f'Close Price Buy/Sell Signals using {strategy}.  Last Signal: {last_signal}'
        fig.suptitle(f'Top: {company.symbol} Stock Price. Bottom: {strategy}')

        if not data[f'{strategy}_Buy'].isnull().all():
            axs[0].scatter(data.index, data[f'{strategy}_Buy'], color='green', label='Buy Signal', marker='^', alpha=1)
        if not data[f'{strategy}_Sell'].isnull().all():
            axs[0].scatter(data.index, data[f'{strategy}_Sell'], color='red', label='Sell Signal', marker='v', alpha=1)
        axs[0].plot(company.prices, label='Close Price', color='blue', alpha=0.35)

        plt.xticks(rotation=45)
        axs[0].set_title(title)
        axs[0].set_xlabel('Date', fontsize=18)
        axs[0].set_ylabel('Close Price', fontsize=18)
        axs[0].legend(loc='upper left')
        axs[0].grid()

    def plot_macd(self, company):
        image = f'images/{company.symbol}_macd.png'
        macd = company.technical_indicators

        # Create and plot the graph
        fig, axs = plt.subplots(2, sharex=True, figsize=(13,9))
        self.plot_price_and_signals(fig, company, macd, 'MACD', axs)

        axs[1].plot(macd['MACD'], label=company.symbol+' MACD', color = 'green')
        axs[1].plot(macd['MACD_Signal'], label='Signal Line', color='orange')
        positive = macd['MACD_Histogram'][(macd['MACD_Histogram'] >= 0)]
        negative = macd['MACD_Histogram'][(macd['MACD_Histogram'] < 0)]
        axs[1].bar(positive.index, positive, color='green')
        axs[1].bar(negative.index, negative, color='red')    
        axs[1].legend(loc='upper left')
        axs[1].grid()
        print(os.path.abspath(image))
        plt.savefig(image)
        # plt.show()

    def plot_rsi(self, company):
        image = f'images/{company.symbol}_rsi.png'
        rsi = company.technical_indicators
        low_rsi = 40
        high_rsi = 70

        #plt.style.use('default')
        fig, axs = plt.subplots(2, sharex=True, figsize=(13, 9))
        self.plot_price_and_signals(fig, company, rsi, 'RSI', axs)
        axs[1].fill_between(rsi.index, y1=low_rsi, y2=high_rsi, color='#adccff', alpha=0.3)
        axs[1].plot(rsi['RSI'], label='RSI', color='blue', alpha=0.35)
        axs[1].legend(loc='upper left')
        axs[1].grid()
        plt.savefig(image)
        # plt.show()

    def plot_bollinger_bands(self, company):
        image = f'images/{company.symbol}_bb.png'
        bollinger_bands = company.technical_indicators

        fig, axs = plt.subplots(2, sharex=True, figsize=(13, 9))

        self.plot_price_and_signals(fig, company, bollinger_bands, 'Bollinger_Bands', axs)

        axs[1].plot(bollinger_bands['Bollinger_Bands_Middle'], label='Middle', color='blue', alpha=0.35)
        axs[1].plot(bollinger_bands['Bollinger_Bands_Upper'], label='Upper', color='green', alpha=0.35)
        axs[1].plot(bollinger_bands['Bollinger_Bands_Lower'], label='Lower', color='red', alpha=0.35)
        axs[1].fill_between(bollinger_bands.index, bollinger_bands['Bollinger_Bands_Lower'], bollinger_bands['Bollinger_Bands_Upper'], alpha=0.1)
        axs[1].legend(loc='upper left')
        axs[1].grid()
        plt.savefig(image)
        # plt.show()


class TestTechnicalIndicator():

    def test_tech_indicator(self, symbol):
        company = Company(symbol)
        config = {}
        company.prices = yf.Ticker(company.symbol).history(period='1y')['Close']
        set_technical_indicators(config, company)

        tacp = TechnicalIndicatorsChartPlotter()
        tacp.plot_macd(company)
        tacp.plot_rsi(company)
        tacp.plot_bollinger_bands(company)
