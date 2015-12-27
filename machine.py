import os 
import json
import requests
import apsw

# import flask web microframework
from flask import Flask
from flask import request

# import from the 21 Developer Library
from two1.lib.wallet import Wallet
from two1.lib.bitserv.flask import Payment

app = Flask(__name__)
wallet = Wallet()
payment = Payment(app, wallet)

CURR_PRICE = 'https://api.coindesk.com/v1/bpi/currentprice.json'

# fetch current bitcoin price
@app.route('/quote')
def get_quote():
    q = requests.get(CURR_PRICE)
    if q.content:
        quote = json.loads(q.content)
        usd = quote.get('bpi').get('USD')
        return usd.get('rate_float')

# buy a bitcoin option - require payment at max price, return the change
@app.route('/buy')
@payment.required(1000)
def purchase():
    # calculate option price
    
    # extract payout address from client address
    client_payout_addr = request.args.get('payout_address')

    # return the change
    txid = wallet.send_to(client_payout_addr, 2000)

if __name__ == '__main__':
    app.run(host='0.0.0.0')