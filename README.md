# Stock trading bots

This project contains telegram bots which can be used to get\
fundamental and technical analysis for any requested stock symbol.

## Prerequisites

```
python
heroku account
telegram account
```

## Setting up the project

1. First create an account in Telegram app.
2. Create a bot with any suitable name and username by following steps [here](https://core.telegram.org/bots)
3. Once that is done, note down the api token mentioned which will be needed for later stage.
4. Now create a new heroku account if it doesnt exist.
5. Create a new python app. Select a sutiable name for the app. Under the settings tab,\
   you will see instructions on howto deploy the code. Repeat the same steps for all bots/heroku app

## Configuring the code

1. In the `app.py` file of each directory, copy paste the api token of telegram bot under `TOKEN` variable.
2. Under the `set_webhook` function of `app.py` file, add your app name obtained from heroku.
3. Now deploy each of the app by following the instructions mentioned on the heroku deploy page.
4. If the deploy is successful, navigate to `https://<YOUR APP NAME>.herokuapp.com/setwebhook` to setup the webhook needed for telegram bot.
5. You should see the message `webhook setup ok` else see whats going on by looking at the logs of your app using `heroku logs --tail`
6. If the webhook setup is successful, goto your bot and send `/start` message.
7. Now request the data for any stock by sending message like `tsla` or `aapl` or any other symbol

## Fundamental analysis

The bot present under `fundamental-analysis` folder provides only the fundamental data for the stock\
whereas the bot present under `technical-analysis` folder provides MACD, RSI and bollinger band diagram\
in the telegram.

## Getting stocks earnings report

The bot present under the directory `stocks-earnings-date` sends a message containing the list of\
companies who have earnings report in the user specified date range.\
The dates has to be specified in the form `<YYYY-MM-DD>`.

If you want to get list of companies who are reporting earnings for a week then you can spcify\
`2020-01-01 2021-01-07`.

If you want the earnings list only for a particular day then you can enter\
`2020-03-18`

If you want to get the list auotmatically every week then you need to setup a crontab to execute\
the script `earnings_date_cron.py`. I prefer to execute this script on every sunday at 9AM

`0 9 * * 0 python3 earnings_date_cron.py`

Dont forget the to change the `TOKEN` and `MY_CHAT_ID` to your bot api token and your chat id respectively.