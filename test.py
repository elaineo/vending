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
from orderbook import add_to_book, get_order_book

app = Flask(__name__)

PAYMENT_REQ = 1000
CURR_PRICE = 'https://api.coindesk.com/v1/bpi/currentprice.json'


# fetch current bitcoin price
def get_quote():
    q = requests.get(CURR_PRICE)
    if q.content:
        quote = json.loads(q.content)
        usd = quote.get('bpi').get('USD')
        return usd.get('rate_float')

# fetch current bitcoin price
@app.route('/quote')
def price_quote():
    q = get_quote()
    return '%.5f' % q

# buy a bitcoin option - require payment at max price, return the change
@app.route('/buy')
def purchase():
    # extract payout address from client address
    client_payout_addr = request.args.get('payout_address')
    # price movement: up or down
    action = request.args.get('action')

    usd_rate = get_quote()

    # add to book
    if action == 'up':
        change = add_to_book(client_payout_addr, PAYMENT_REQ, usd_rate, True)
    else:
        change = add_to_book(client_payout_addr, PAYMENT_REQ, usd_rate, False)
    return '%d' % change

@app.route('/show')
def show_book():
    book = get_order_book()
    return json.dumps(book.dump_all())

if __name__ == '__main__':
    app.run()