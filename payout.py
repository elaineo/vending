"""  Expiry/payout manager
"""

from orderbook import Order


def execute_orders(conn):
    c = conn.cursor()
    orders = []
    day_ago = datetime.now() - timedelta(hours=24)
    for is_buy, address, usd_rate, price in c.execute("SELECT * FROM orders \
        WHERE created_at >= ? ORDER BY created_at", day_ago):
        orders.append(Order(is_buy, address, usd_rate, price))
    c.execute("UPDATE orders SET is_buy = -1 WHERE created_at >= ?", day_ago)
    return orders

def get_oldest(conn):
    c = conn.cursor()
    for created_at in c.execute("SELECT min(created_at) FROM orders WHERE is_buy >= 0"):
        return created_at

def execute_payout(conn, wallet, usd_rate, payout):
    orders = execute_orders(conn)
    for o in orders:
        if o.is_buy == 1 and usd_rate > o.usd_rate or \
            o.is_buy == 0 and usd_rate < o.usd_rate:
            wallet.send_to(o.payout_address, payout)
    # get the next newest 
    next_date = get_oldest(conn)
    return next_date

def execute_mock(conn, wallet, usd_rate, payout):
    orders = execute_orders(conn)
    total_payout = 0
    for o in orders:
        if o.is_buy == 1 and usd_rate > o.usd_rate or \
            o.is_buy == 0 and usd_rate < o.usd_rate:
            total_payout += payout
    print("Total Payout: %d" % total_payout)
    # get the next newest 
    next_date = get_oldest(conn)
    return next_date
