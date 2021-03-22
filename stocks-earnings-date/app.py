# https://towardsdatascience.com/how-to-download-the-public-companies-earnings-calendar-with-python-9241dd3d15d

import pandas as pd
from datetime import datetime
from datetime import timedelta
from yahoo_earnings_calendar import YahooEarningsCalendar
import dateutil.parser
import os
import telegram
from flask import Flask, request


app = Flask(__name__)
TOKEN = '<YOUR BOT API TOKEN>'
bot = telegram.Bot(token=TOKEN)


@app.route('/')
def index():
    return 'wonderful. this works'


@app.route('/setwebhook', methods=['GET', 'POST'])
def set_webhook():
    s = bot.setWebhook('https://<YOUR HEROKU APP NAME>.herokuapp.com/{HOOK}'.format(HOOK=TOKEN))
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
        Welcome to Stocks Earnings Date bot.
        The bot sends the list of stock symbol for whom the earnings date are in the next week.
        You can also enter the custom date range separated by space in the <YYYY-MM-DD> format.
        You can also enter just one date to get earnings report on a particular day.
        """
        print('Received a start request from chat id ' + str(chat_id) + ' and msg id ' + str(msg_id))
        # send the welcoming message
        bot.sendMessage(chat_id=chat_id, text=bot_welcome, reply_to_message_id=msg_id)
    else:
        try:
            # clear the message we got from any non alphabets
            dates = text.split()
            start = dates[0]
            end = start
            start_date = datetime.fromisoformat(start)
            earnings_list = ""
            yec = YahooEarningsCalendar()
            if (len(dates) > 1):
                end = dates[1]
                end_date = datetime.fromisoformat(end)
                print('Getting data for the date range ' + str(start_date) + ' till ' + str(end_date))
                earnings_list = yec.earnings_between(start_date, end_date)
            else:
                print('Getting data for the date ' + str(start_date))
                earnings_list = yec.earnings_on(start_date)

            # saving the data in a pandas DataFrame
            earnings_df = pd.DataFrame(earnings_list)

            result = ""
            count = 0
            for index, row in earnings_df.iterrows():
                result = result + row['ticker'] + "\n"
                count = count + 1

            if count == 0:
                bot.sendMessage(chat_id=chat_id, text="None")
            else:
                msg = str(count) + " companies have earnings between " + start + " and " + end
                bot.sendMessage(chat_id=chat_id, text=msg)
                bot.sendMessage(chat_id=chat_id, text=result)
        except Exception as e:
            print('Exception is ' + str(e))
            # if things went wrong
            bot.sendMessage(chat_id=chat_id, text="There was a problem in the date range your entered, please enter proper date range separated by space", reply_to_message_id=msg_id)

    return 'ok'
