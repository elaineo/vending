import json
import requests

# import flask web microframework
from flask import Flask

import atexit
import threading
from datetime import datetime, timedelta

from payout import execute_payout, execute_mock

PaymentLock = threading.Lock()
PaymentThread = threading.Thread()

# remove for dev env
# wallet = Wallet()
wallet = None

PAYMENT_REQ = 1000
CURR_PRICE = 'https://api.coindesk.com/v1/bpi/currentprice.json'

# fetch current bitcoin price
def get_quote():
    q = requests.get(CURR_PRICE)
    if q.content:
        quote = json.loads(q.content)
        usd = quote.get('bpi').get('USD')
        return usd.get('rate_float')

def vending_machine():
    app = Flask(__name__)

    def interrupt():
        global PaymentThread
        #PaymentThread.cancel()

    def doPayment():
        global wallet
        global PAYMENT_REQ
        global get_quote
        global PaymentThread

        usd_rate = get_quote()

        with PaymentLock:
            PaymentLock.acquire()
            #next_date = execute_payout(conn, wallet, usd_rate, PAYMENT_REQ)
            #next_date = execute_mock(conn, wallet, usd_rate, PAYMENT_REQ)
            Paymentlock.release()

        # Set the next event to happen
        wait = datetime.now() + timedelta(hours=24) - next_date
        PaymentThread = threading.Timer(wait.total_seconds(), doPayment)
        PaymentThread.start()   

    def doPaymentStart():
        global PaymentThread
        wait = timedelta(hours=24)
        PaymentThread = threading.Timer(wait.total_seconds(), doPayment)
        PaymentThread.start()

    # Initiate
    # doPaymentStart()
    # clear the trigger for the next thread
    atexit.register(interrupt)
    return app