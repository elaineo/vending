""" Dummy test env without 21 computer
"""

import os 
import json
import requests
import logging

# import flask web microframework
from flask import Flask
from flask import request

# vending machine stuff
from orderbook import add_to_book

app = Flask(__name__)

PAYMENT_REQ = 1000
CURR_PRICE = 'https://api.coindesk.com/v1/bpi/currentprice.json'

# fetch current bitcoin price
@app.route('/quote')
def get_quote():
    q = requests.get(CURR_PRICE)
    if q.content:
        quote = json.loads(q.content)
        usd = quote.get('bpi').get('USD')
        return '%.5f' % usd.get('rate_float')

# buy a bitcoin option - require payment at max price, return the change
@app.route('/buy')
def purchase():
    logging.info("buy")
    # extract payout address from client address
    client_payout_addr = request.args.get('payout_address')
    # price movement: up or down
    action = request.args.get('action')

    # add to book
    if action == 'up':
        change = add_to_book(client_payout_addr, PAYMENT_REQ, True)
    else:
        change = add_to_book(client_payout_addr, PAYMENT_REQ, False)
    return change

if __name__ == '__main__':
    app.run()