import json
import os
import sys

# import from the 21 Developer Library
from two1.commands.config import Config
from two1.lib.wallet import Wallet
from two1.lib.bitrequests import BitTransferRequests

# set up bitrequest client for BitTransfer requests
wallet = Wallet()
username = Config().username
requests = BitTransferRequests(wallet, username)

# server address
SERVER_URL = 'http://localhost:5000/'

def cmd_btc_quote():
    url = SERVER_URL + 'btc_quote'
    r = requests.get(url)
    print(r.text)

def cmd_price_quote():
    url = SERVER_URL + 'quote'
    r = requests.get(url)
    print(r.text)

def cmd_buy(action):
    url = SERVER_URL + 'buy?action=%s&payout_address=%s' % \
                        (action, wallet.get_payout_address())
    r = requests.get(url)
    print(r.text)

if __name__ == '__main__':
    if sys.argv[1] == 'quote':
        cmd_price_quote()
    elif sys.argv[1] == 'buy':
        cmd_buy(sys.argv[2])
    else:
        cmd_price_quote()
