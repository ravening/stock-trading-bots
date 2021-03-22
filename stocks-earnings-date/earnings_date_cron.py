import pandas as pd
from datetime import datetime
from datetime import timedelta
from yahoo_earnings_calendar import YahooEarningsCalendar
import dateutil.parser
import os
import telegram


TOKEN = '<YOUR BOT API TOKEN>'
bot = telegram.Bot(token=TOKEN)
DAYS_AHEAD = 7
MY_CHAT_ID = <YOUR CHAT ID>

start_date = datetime.now().date()
end_date = (datetime.now().date() + timedelta(days=DAYS_AHEAD))

yec = YahooEarningsCalendar()
earnings_list = yec.earnings_between(start_date, end_date)

earnings_df = pd.DataFrame(earnings_list)

result = ""
count = 0
for index, row in earnings_df.iterrows():
    result = result + row['ticker'] + "\n"
    count = count + 1

if count > 0:
    msg = str(count) + " companies have earnings this week"
    bot.sendMessage(chat_id=MY_CHAT_ID, text=msg)
    bot.sendMessage(chat_id=MY_CHAT_ID, text=result)
