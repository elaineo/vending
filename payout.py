"""  Expiry/payout manager
"""

import apsw

conn = apsw.Connection("book.db")

def execute_orders():
    c = conn.cursor()
    day_ago = datetime.now() - timedelta(hours=24)
    c.execute("SELECT * FROM orders WHERE created_at >= ? ORDER BY created_at", day_ago)
    orders = c.fetch_all()
    c.execute("UPDATE orders SET is_buy = -1 WHERE created_at >= ?", day_ago)
    return orders

def get_oldest():
    c = conn.cursor()
    for created_at in c.execute("SELECT min(created_at) FROM orders WHERE is_buy >= 0"):
        return created_at

def execute_payout(wallet, usd_rate, payout):
    orders = execute_orders()
    for o in orders:
        if o.is_buy == 1 and self.usd_rate > o.usd_rate or \
            o.is_buy == 0 and self.usd_rate < o.usd_rate:
            wallet.send_to(o.payout_address, self.payout)
    # get the next newest 
    next_date = get_oldest()
    return next_date

def execute_mock(wallet, usd_rate, payout):
    orders = execute_orders()
    total_payout = 0
    for o in orders:
        if o.is_buy == 1 and self.usd_rate > o.usd_rate or \
            o.is_buy == 0 and self.usd_rate < o.usd_rate:
            total_payout += self.payout
    print("Total Payout: %d" % total_payout)
    # get the next newest 
    next_date = get_oldest()
    return next_date
