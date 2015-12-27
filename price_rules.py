"""  Logarithmic market scoring rule market maker

General cost function:
    C = B * ln(e^(q1/B)+e^(q2/B))

    q1 is the number of outstanding BUYERS
    q2 is the number of outstanding SELLERS

    B_FACTOR is related to the market-maker's max loss for each 24-hour period.

    SPREAD is a constant that represents the "cut" taken by the market-maker.

    TODO: normalize q with regards to expiry date
"""
import math
import random
import logging

B_FACTOR = 90  # results in a max loss of about 10
DEFAULT_SPREAD = 0.0
DEFAULT_MIN = 0.01
DEFAULT_MAX = 1.00

def cost_function(buys, sells):
    """ Returns the total amount that users have collectively spent so far """
    c = B_FACTOR * math.log( math.exp(buys/B_FACTOR) + math.exp(sells/B_FACTOR))
    return c

def calc_cost(is_buy=True):
    """ calculate price given an order
        can only buy one at a time
    """
    buys, sells = net_options_out()
    if is_buy:
        new_cost_func = cost_function(buys+1, sells)
    else:
        new_cost_func = cost_function(buys, sells+1)
    old_cost_func = cost_function(buys, sells)
    price = new_cost_func - old_cost_func

    # add spread here if desired
    price_adj = price * (DEFAULT_MAX - DEFAULT_MIN) + DEFAULT_MIN
    return price_adj

#def net_options_out(key):
    # count outstanding db items