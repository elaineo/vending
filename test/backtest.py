import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from price_rules import *

from random import randint

# import old price quotes

class BackTest(unittest.TestCase):

  def test_loss_bounds(self):
    # for each item in quote_stream
    for _ in range(100):
      buys = randint(0,100)
      sells = randint(0,100)
      if buys > sells:
        self.assertGreater(price_function(buys,buys,sells), 0.500)
        self.assertLess(price_function(sells,buys,sells), 0.500)
      else:
        self.assertLessEqual(price_function(buys,buys,sells), 0.500)
        self.assertGreaterEqual(price_function(sells,buys,sells), 0.500, msg='{0},{1}'.format(buys, sells))

  def test_calc_cost(self):
    for _ in range(100):
      buys = randint(0,100)
      sells = randint(0,100)
      if buys > sells:
        self.assertGreater(calc_cost(buys, sells, True), 0.5)
        self.assertLess(calc_cost(buys, sells, False), 0.505)
      else:
        self.assertGreaterEqual(calc_cost(buys, sells, False), 0.5)
        self.assertLessEqual(calc_cost(buys, sells, True), 0.505)


if __name__ == '__main__':
  unittest.main()