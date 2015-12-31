"""  OrderBook/db manager
"""

from datetime import datetime, timedelta

from price_rules import calc_cost

def add_to_book(conn, address, payment, usd_rate, is_buy=True):
    # fetch book
    book = get_order_book(conn, usd_rate)
    cost = book.get_quote(is_buy)

    adj_payment = int(round(cost*payment))
    order = Order(is_buy, address, usd_rate, adj_payment)
    add_order_book(conn, order)

    change = payment - adj_payment
    return change

def get_book_quote(conn, usd_rate):
    book = get_order_book(usd_rate=None)
    buy_cost = book.get_quote(True)
    sell_cost = book.get_quote(False)
    return buy_cost, sell_cost

def get_order_book(conn, usd_rate=None):
    c = conn.cursor()
    orders = []
    if usd_rate:
        query = "SELECT is_buy, payout_address, usd_rate, price FROM orders \
                    WHERE (is_buy = 0 AND usd_rate <= %.5f) OR \
                    (is_buy = 1 AND usd_rate >= %.5f) \
                    ORDER BY created_at" % (usd_rate, usd_rate)
    else:
        query = "SELECT is_buy, payout_address, usd_rate, price FROM orders \
                    WHERE is_buy >= 0 ORDER BY created_at"
    for is_buy, address, usd_rate, price in c.execute(query):
        orders.append(Order(is_buy, address, usd_rate, price))
    return OrderBook(orders)

def add_order_book(conn, order):
    c = conn.cursor()
    insert = "INSERT INTO orders(is_buy, payout_address, usd_rate, price) \
                    values(:is_buy, :payout_address, :usd_rate, :price)"
    c.execute(insert, {"is_buy": order.is_buy, 
                        "payout_address": order.payout_address,
                        "usd_rate": order.usd_rate,
                        "price": order.price})

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
            cost = calc_cost(num_buys+1, num_sells, True)
        else:
            cost = calc_cost(num_buys, num_sells+1, False)
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