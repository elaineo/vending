# Vending Machine for Binary Options

## 21 Bitcoin Computer that sells 24-hour binary options on BTCUSD

Prices are dynamically set by the internal market maker based on a logarithmic market scoring rule.

Options can be purchased at any time, and always expire 24 hours from time of purchase. A background process issues payments as options expire.

### Client Commands

1. Get price quote
--------------------

HTTP URI: /quote

Result: 
  Current BTCUSD rate in USD, Buy price and Sell price in satoshis

<b>Note:</b> Buying means the BTCUSD rate will be higher in 24 hours. Selling is a bet on a downward move. 

2. Buy an option
--------------------

HTTP URI: /buy

Params: action (up/down) 

Result: 
  The amount paid in satoshis and the current BTCUSD price.

Example:
 $ /buy?action=up

This buys an option indicating that the BTCUSD rate will be higher tomorrow.

### Running the server

	$ python3 server.py
