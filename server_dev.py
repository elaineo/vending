""" Dummy test env without 21 computer
"""

import os 
import json
import requests
import logging

import sqlite3
from flask import g

# import flask web microframework
from flask import Flask
from flask import request

# vending machine stuff
from orderbook import add_to_book, get_order_book, get_book_quote
import machine_app

DATABASE = "book.db"

def get_db(app):
    with app.app_context():
        db = getattr(g, '_database', None)
        if db is None:
            db = g._database = connect_to_database()
        return db
        
def connect_to_database():
    return sqlite3.connect(DATABASE)

app = machine_app.vending_machine()
conn = get_db(app)

# fetch current bitcoin price
@app.route('/btc_quote')
def btc_quote():
    q = machine_app.get_quote()
    return '%.5f' % q

# fetch option price
@app.route('/quote')
def price_quote():
    logging.info("quote")
    q = machine_app.get_quote()
    buy_price, sell_price = get_book_quote(conn, q)
    return 'buy: %.5f, sell: %.5f' % (buy_price, sell_price)

# buy a bitcoin option - require payment at max price, return the change
@app.route('/buy')
def purchase():
    # extract payout address from client address
    client_payout_addr = request.args.get('payout_address')
    # price movement: up or down
    action = request.args.get('action')

    usd_rate = machine_app.get_quote()

    # add to book
    if action == 'up':
        change = add_to_book(conn, client_payout_addr, machine_app.PAYMENT_REQ, usd_rate, True)
    else:
        change = add_to_book(conn, client_payout_addr, machine_app.PAYMENT_REQ, usd_rate, False)
    return '%d' % change

@app.route('/show')
def show_book():
    book = get_order_book(conn)
    return json.dumps(book.dump_all())

if __name__ == '__main__':
    app.run()