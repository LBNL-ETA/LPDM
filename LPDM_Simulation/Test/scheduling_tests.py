import unittest

""" This was an unused function that was designed to interleave Utility Meter buy and sell prices. Was not the most 
effective implementation. """

def make_buy_sell_schedule(sell_schedule, buy_schedule):
    DEFAULT_NEXT = (None, None)

    buy_sell_schedule = []

    sell_iter = sell_schedule.__iter__()
    buy_iter = buy_schedule.__iter__()
    sell_time_curr, sell_price_curr = next(sell_iter, DEFAULT_NEXT)
    buy_time_curr, buy_price_curr = next(buy_iter, DEFAULT_NEXT)

    buy_price_prev = None
    sell_price_prev = None

    while sell_time_curr is not None and buy_time_curr is not None:
        if sell_time_curr < buy_time_curr:
            buy_sell_schedule.append((sell_time_curr, sell_price_curr, buy_price_prev))
            sell_price_prev = sell_price_curr
            sell_time_curr, sell_price_curr = next(sell_iter, DEFAULT_NEXT)
        elif buy_time_curr < sell_time_curr:
            buy_sell_schedule.append((buy_time_curr, sell_price_prev, buy_price_curr))
            buy_price_prev = buy_price_curr
            buy_time_curr, buy_price_curr = next(buy_iter, DEFAULT_NEXT)
        else:
            buy_sell_schedule.append((sell_time_curr, sell_price_curr, buy_price_curr))
            sell_price_prev = sell_price_curr
            buy_price_prev = buy_price_curr
            sell_time_curr, sell_price_curr = next(sell_iter, DEFAULT_NEXT)
            buy_time_curr, buy_price_curr = next(buy_iter, DEFAULT_NEXT)

    while sell_time_curr is not None:
        buy_sell_schedule.append((sell_time_curr, sell_price_curr, buy_price_prev))
        sell_time_curr, sell_price_curr = next(sell_iter, DEFAULT_NEXT)

    while buy_time_curr is not None:
        buy_sell_schedule.append((buy_time_curr, sell_price_prev, buy_price_curr))
        buy_time_curr, buy_price_curr = next(buy_iter, DEFAULT_NEXT)

    return buy_sell_schedule

class test_utility_buy_sell_schedules(unittest.TestCase):

    def test1(self):
        buy_schedule = [(0, .1), [6, .15]]
        sell_schedule = [(0, .2), (5, .15), (6, .1)]
        bs = make_buy_sell_schedule(sell_schedule=sell_schedule, buy_schedule=buy_schedule)
        self.assertEqual(bs, [(0, 0.2, 0.1), (5, 0.15, 0.1), (6, 0.1, .15)])

    def test2(self):
        buy_schedule = [(3, .1), [6, .15]]
        sell_schedule = [(0, .2), (5, .15), (6, .1), (9, .2), (12, .4)]
        bs = make_buy_sell_schedule(sell_schedule=sell_schedule, buy_schedule=buy_schedule)
        self.assertEqual(bs, [(0, 0.2, None), (3, 0.2, .1), (5, .15, .1), (6, 0.1, .15), (9, .2, .15), (12, .4, .15)])
        print(bs)

if __name__ == 'main':
    unittest.main()