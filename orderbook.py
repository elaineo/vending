"""  OrderBook/db manager
"""

import apsw
from datetime import datetime, timedelta

from price_rules import calc_cost

conn = apsw.Connection("book.db")

def add_to_book(address, payment, usd_rate, is_buy=True):
    # fetch book
    book = get_order_book()
    cost = book.get_quote(is_buy)

    adj_payment = int(round(cost*payment))
    order = Order(is_buy, address, usd_rate, adj_payment)
    add_order_book(order)

    change = payment - adj_payment
    return change

def get_order_book():
    c = conn.cursor()
    orders = []
    for is_buy, address, usd_rate, price in \
        c.execute("SELECT is_buy, payout_address, usd_rate, price FROM orders \
                    WHERE is_buy >= 0 ORDER BY created_at"):
        orders.append(Order(is_buy, address, usd_rate, price))
    return OrderBook(orders)

def add_order_book(order):
    c = conn.cursor()
    insert = "INSERT INTO orders(is_buy, payout_address, usd_rate, price) \
                    values(:is_buy, :payout_address, :usd_rate, :price)"
    c.execute(insert, {"is_buy": order.is_buy, 
                        "payout_address": order.payout_address,
                        "usd_rate": order.usd_rate,
                        "price": order.price})


def execute_orders():
    # this should be in a transaction with payout
    c = conn.cursor()
    day_ago = datetime.now() - timedelta(hours=24)
    c.execute("SELECT * FROM orders WHERE created_at >= ? ORDER BY created_at", day_ago)
    orders = c.fetch_all()
    c.execute("UPDATE orders SET is_buy = -1 WHERE created_at >= ?", day_ago)
    return orders

class OrderBook(object):

    def __init__(self, orders):
        self.orders = orders

    def buys(self):
        buys = [o for o in self.orders if o.is_buy == 1]
        return buys

    def sells(self):
        sells = [o for o in self.orders if o.is_buy == 0]
        return sells

    def top_of_book(self):
        if self.orders is None:
            return None
        else:
            return self.orders[0]

    def net_options_out(self):
        return len(self.buys()), len(self.sells())

    def get_quote(self, is_buy=True):
        # calculate option price
        num_buys, num_sells = self.net_options_out()
        if is_buy:
            cost = calc_cost(num_buys, num_sells, True)
        else:
            cost = calc_cost(num_buys, num_sells, False)
        return cost

    def dump_all(self):
        return [o.to_json() for o in self.orders]

class Order(object):

    def __init__(self, is_buy, payout_address, usd_rate, price):
        self.is_buy = is_buy  # set to -1 to archive
        self.payout_address = payout_address  # user's btc address
        self.usd_rate = usd_rate  # bitcoin price
        self.price = price  # what the user paid; for bookkeeping only

    def to_json(self):
        return {
            "is_buy": self.is_buy,
            "payout_address": self.payout_address,
            "usd_rate": self.usd_rate,
            "price_paid": self.price
        }