import re
from flask import Flask, request
import telegram
import asyncio
import yahoo_fin.stock_info as si
import pandas


TOKEN = '<YOUR BOT API'
bot = telegram.Bot(token=TOKEN)

app = Flask(__name__)


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
        Welcome to Stocks Fundamental analysis bot.
        The bot sends the fundamental analysis data of the requested stock symbol.
        """
        # send the welcoming message
        bot.sendMessage(chat_id=chat_id, text=bot_welcome, reply_to_message_id=msg_id)

    else:
        try:
            # clear the message we got from any non alphabets
            config = {}
            text = re.sub(r"\W", "_", text)
            company = Company(text.upper())
            print('getting data for company ' + text.upper())

            get_fundamental_indicators_for_company(config, company)
            result = ""
            for key in company.fundamental_indicators:
                result += '{:<30}{:40}\n'.format(str(key), str(company.fundamental_indicators[key]))
            bot.sendMessage(chat_id=chat_id, text=result)
        except Exception as e:
            print('Exception is ' + str(e))
            # if things went wrong
            bot.sendMessage(chat_id=chat_id, text="There was a problem in the name you used, please enter proper name", reply_to_message_id=msg_id)

    return 'ok'


def get_fundamental_indicators_for_company(config, company):
    print('getting the fundamental indicators')
    company.fundamental_indicators = {}

    data = si.get_quote_table(company.symbol.upper())
    company.fundamental_indicators = data

    keys = {
        'Market Cap (intraday) 5': 'MarketCap',
        'Price/Sales (ttm)': 'PS',
        'Trailing P/E': 'PE',
        'PEG Ratio (5 yr expected) 1': 'PEG',
        'Price/Book (mrq)': 'PB'
    }

    data = si.get_stats_valuation(company.symbol)
    get_data_item(company.fundamental_indicators, data, keys)

    # Income statement and Balance sheet
    data = get_statatistics(company.symbol)
    get_data_item(company.fundamental_indicators, data,
                {
                    'Profit Margin': 'ProfitMargin',
                    'Operating Margin (ttm)': 'OperMargin',
                    'Current Ratio (mrq)': 'CurrentRatio',
                    'Payout Ratio 4': 'DivPayoutRatio'
                })

    get_last_data_item(company.fundamental_indicators, data,
            {
                'Return on assets': 'ROA',
                'Return on equity': 'ROE',
                'Total cash per share': 'Cash/Share',
                'Book value per share': 'Book/Share',
                'Total debt/equity': 'Debt/Equity'
            })


class Company:
    def __init__(self, symbol):
        self.symbol = symbol
        self.fundamental_indicators = {}


def to_float(val):
    if val == 0:
        return float(0)

    val = str(val).upper()

    if '%' in val:
        return round(float(val[:-1]), 4)

    m = {'K': 3, 'M': 6, 'B': 9, 'T': 12}

    for key in m.keys():
        if key in val:
            multiplier = m.get(val[-1])
            return round(float(val[:-1]) * (10 ** multiplier), 4)
    return round(float(val), 4)


def get_statatistics(symbol):
    url = f"https://finance.yahoo.com/quote/{symbol}/key-statistics?p={symbol}"
    dataframes = pandas.read_html(url)
    return pandas.concat(dataframes[1:])


def get_data_item(result, dataframe, columns):
    for column_to_find, column_to_name in columns.items():
        try:
            result[column_to_name] = list((dataframe.loc[dataframe[0] == column_to_find].to_dict()[1]).values())[0]
        except Exception as ex:
            result[column_to_name] = 'NA'
    result = dataframe


def get_last_data_item(result, dataframe, columns):
    data = dataframe.iloc[:, :2]
    data.columns = ["Column", "Last"]

    for column_to_find, column_to_name in columns.items():
        try:
            val = data[data.Column.str.contains(column_to_find, case=False, regex=True)].iloc[0, 1]
            float_val = to_float(val)
            result[column_to_name] = float_val
        except Exception as ex:
            result[column_to_name] = "NA"


if __name__ == '__main__':
    app.run(host='0.0.0.0', threaded=True)
