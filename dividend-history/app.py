from datetime import datetime, timedelta
import time, requests, pandas, lxml
from lxml import html
import telegram
from flask import Flask, request
import re


app = Flask(__name__)

TOKEN = 'YOUR BOT API TOKEN'
bot = telegram.Bot(token=TOKEN)


@app.route('/')
def index():
    return 'wonderful. this works'


@app.route('/setwebhook', methods=['GET', 'POST'])
def set_webhook():
    s = bot.setWebhook('https://YOUR BOT NAME.herokuapp.com/{HOOK}'.format(HOOK=TOKEN))
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
    # the first time you chat with the bot AKA the welcoming message
    if text == "/start":
        # print the welcoming message
        bot_welcome = """
        Welcome to Dividends History bot.
        The bot sends the dividend history for the requested stock symbol.
        Please enter only the ticket symbol and not the company name
        """
        print('Received a start request from chat id ' + str(chat_id) + ' and msg id ' + str(msg_id))
        # send the welcoming message
        bot.sendMessage(chat_id=chat_id, text=bot_welcome, reply_to_message_id=msg_id)
    else:
        try:
            # clear the message we got from any non alphabets
            text = re.sub(r"\W", "_", text)
            print('Getting data for company ' + text.upper())
            data = process_data(text.upper())
            bot.sendMessage(chat_id=chat_id, text=data)
        except Exception as e:
            print('Exception is ' + str(e))
            # if things went wrong
            bot.sendMessage(chat_id=chat_id, text="There was a problem in the name you used, please enter proper name", reply_to_message_id=msg_id)

    return 'ok'


def format_date(date_datetime):
    date_timetuple = date_datetime.timetuple()
    date_mktime = time.mktime(date_timetuple)
    date_int = int(date_mktime)
    date_str = str(date_int)
    return date_str


def subdomain(symbol, start, end):
    format_url = "{0}/history?period1={1}&period2={2}"
    tail_url = "&interval=div%7Csplit&filter=div&frequency=1d"
    subdomain = format_url.format(symbol, start, end) + tail_url
    return subdomain


def header(subdomain):
    hdrs = {"authority": "finance.yahoo.com",
            "method": "GET",
            "path": subdomain,
            "scheme": "https",
            "accept": "text/html,application/xhtml+xml",
            "accept-encoding": "gzip, deflate, br",
            "accept-language": "en-US,en;q=0.9",
            "cache-control": "no-cache",
            "dnt": "1",
            "pragma": "no-cache",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "same-origin",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1",
            "user-agent": "Mozilla/5.0"}
    return hdrs


def scrape_page(url, header):
    page = requests.get(url)
    element_html = html.fromstring(page.content)
    table = element_html.xpath('//table')
    table_tree = lxml.etree.tostring(table[0], method='xml')
    pandas.set_option("display.max_rows", None, "display.max_columns", None)
    panda = pandas.read_html(table_tree)
    return panda


def clean_dividends(symbol, dividends):
    index = len(dividends)
    dividends = dividends.drop(index-1)
    dividends = dividends.set_index('Date')
    dividends = dividends['Dividends']
    dividends = dividends.str.replace(r'\Dividend', '', regex=True)
    dividends = dividends.astype(float)
    dividends.name = symbol
    return dividends


def process_data(symbol):
    # create datetime objects
    start = datetime.today() - timedelta(days=9125)
    end = datetime.today()
    # properly format the date to epoch time
    start = format_date(start)
    end = format_date(end)
    # format the subdomain
    sub = subdomain(symbol, start, end)
    # customize the request header
    hdrs = header(sub)

    # concatenate the subdomain with the base URL
    base_url = "https://finance.yahoo.com/quote/"
    url = base_url + sub

    # scrape the dividend history table from Yahoo Finance
    dividends = scrape_page(url, hdrs)

    # clean the dividend history table
    clean_div = clean_dividends(symbol, dividends[0])
    return str(clean_div)
