import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import mock
import unittest
from payout import *

from random import randint

class MockWallet(object):
  def send_to(self, address, payout):
    pass

def mock_execute_orders():
  data = [[True,400],[True,500],[False,300],[False,500]]
  return [Order(d[0], "blah", d[1], 999) for d in data]

class TestPayout(unittest.TestCase):

  @mock.patch('payout.execute_orders', side_effect=mock_execute_orders)
  @mock.patch('payout.get_oldest', return_value='tomorrow')
  def test_execute_payout(self, m0, m1):
    wallet = mock.Mock(spec = MockWallet)
    next_date = execute_payout(wallet, 450, 1000)
    wallet.send_to.assert_called_with("blah", 1000)
    self.assertEqual(next_date, 'tomorrow')
    
if __name__ == '__main__':
  unittest.main()