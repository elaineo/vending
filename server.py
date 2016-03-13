import yaml

import os 
import json
import requests
import logging

import sqlite3
from flask import g
from flask import send_from_directory

# import from the 21 Developer Library
from two1.lib.wallet import Wallet
from two1.lib.bitserv.flask import Payment

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
payment = Payment(app, machine_app.wallet)

# fetch current bitcoin price
@app.route('/btc_quote')
def btc_quote():
    logging.info("btc_quote")
    q = machine_app.get_quote()
    return '%.5f' % q

# fetch option price
@app.route('/quote')
def price_quote():
    logging.info("quote")
    q = machine_app.get_quote()
    buy_price, sell_price = get_book_quote(conn, q)
    return 'BTCUSD: %.5f  buy: %.5f, sell: %.5f' % (q, buy_price, sell_price)
    
# buy a bitcoin option - require payment at max price, return the change
@app.route('/buy')
@payment.required(machine_app.PAYMENT_REQ)
def purchase():
    logging.info("buy")
    # extract payout address from client address
    client_payout_addr = request.args.get('payout_address')
    # price movement: up or down
    action = request.args.get('action')

    if not client_payout_addr:
        return "Required: payout_address. You know, for when you win."
    if not action:
        return "Required: action"

    usd_rate = machine_app.get_quote()

    # add to book
    if action == 'up':
        change = add_to_book(conn, client_payout_addr, machine_app.PAYMENT_REQ, usd_rate, True)
    else:
        change = add_to_book(conn, client_payout_addr, machine_app.PAYMENT_REQ, usd_rate, False)

    try:
        txid = machine_app.wallet.send_to(client_payout_addr, change)
    except ValueError:
        txid = machine_app.wallet.send_to(client_payout_addr, machine_app.PAYMENT_REQ)
        return "Ugh, dust problem. Payment refunded"
    return "Paid %d. BTCUSD is currently %.5f and will go %s." % \
            (machine_app.PAYMENT_REQ - change, usd_rate, action)

@app.route('/show')
def show_book():
    logging.info("show")
    book = get_order_book(conn)
    return json.dumps(book.dump_all())

@app.route('/manifest')
def docs():
    '''
    Serves the app manifest to the 21 crawler.
    '''
    with open('manifest.yaml', 'r') as f:
        manifest_yaml = yaml.load(f)
    return json.dumps(manifest_yaml)

@app.route('/client')
def client():
    '''
    Provides an example client script.
    '''
    return send_from_directory('static', 'client.py')

if __name__ == '__main__':
    app.run(host='0.0.0.0')
