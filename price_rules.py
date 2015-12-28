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
import logging

B_FACTOR = 15.000  # results in a max loss of about 10
DEFAULT_SPREAD = 0.0
DEFAULT_MIN = 0.001
DEFAULT_MAX = 1.000
RANGE = DEFAULT_MAX - DEFAULT_MIN

def price_function(q, buys, sells):
    c = math.exp(q/B_FACTOR) / ( math.exp(buys/B_FACTOR) + math.exp(sells/B_FACTOR))
    return c

def calc_cost(buys, sells, is_buy=True):
    """ calculate price given an order
        can only buy one at a time
    """
    if is_buy:
        price = price_function(buys, buys, sells)
    else:
        price = price_function(sells, buys, sells)

    price_adj = (1 + DEFAULT_SPREAD) * price * RANGE + DEFAULT_MIN
    return price_adj

def calc_belief(buys, sells):
    belief = price_function(buys, buys, sells)
    return belief