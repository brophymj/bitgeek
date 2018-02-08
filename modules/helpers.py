#!/usr/bin/python3
"""Helpers func for Bittrex Flask app."""
import csv
from datetime import datetime, timedelta
from decimal import Decimal

from bson.son import SON
from modules.bittrex import coins_list, timing
from pymongo import MongoClient

connection = MongoClient()
db = connection.bittrex
collection = db.market


def utcdate():
    """Return properly formatted UTC date for Mongo."""
    return datetime.utcnow().strftime('%m/%d/%Y %I:%M %p')


def to_date(string):
    """Convert string to date."""
    return datetime.strptime(string, '%Y-%m-%dT%H:%M')


def to_string(date):
    """Convert date to string."""
    return datetime.strftime(date, '%Y-%m-%dT%H:%M')


def get_report():
    """Get MongoDB report."""
    report = {}
    try:
        report['count'] = collection.find().count()
        report['from'] = list(collection.find().sort(
            [('TimeStamp', 1)]).limit(1))[0]['TimeStamp']
        report['to'] = list(collection.find().sort(
            [('TimeStamp', -1)]).limit(1))[0]['TimeStamp']
    except:
        pass
    return report or False


def datacenter_report(interval, todate, coin, fast, slow, signal, fromdate):
    """Generate report and CSV file for datacenter endpoint."""
    if coin:
        path = [timing(fromdate), timing(todate), coin, str(interval)]
    else:
        path = [timing(fromdate), timing(todate), 'ALL', str(interval)]
    filepath = '-'.join(path).replace(':', '-')
    with open('archive/{}.csv'.format(filepath), 'w') as dump:
        fieldnames = ['pair', 'interval', 'datetime', 'date',
                      'time', 'volume',
                      'price', 'ema_fast', 'ema_slow', 'macd',
                      'signal_line', 'macd_hist']
        writer = csv.DictWriter(
            dump, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        if coin:
            [writer.writerow(i) for i in summarize(
                interval, todate, coin, fast, slow, signal, fromdate)]
        else:
            for c in coins_list:
                try:
                    [writer.writerow(i) for i in summarize(
                        interval, todate, c, fast, slow, signal, fromdate)]
                except:
                    pass
    return filepath


def summarize(interval, todate, coin, fast, slow, signal, fromdate=False):
    """Get the graph generated."""
    coin = 'BTC-' + coin
    if not fromdate:
        limits = interval * 66
        pipeline =\
            [{"$match":
              {'TimeStamp':
               {"$lt":
                (datetime.strptime(todate,
                                   '%m/%d/%Y %I:%M %p'
                                   ) + timedelta(minutes=1)
                 ).strftime('%Y-%m-%dT%H:%M')},
               'Pair': coin
               }
              },
             {"$group":
                {"_id":
                 {'datehours':
                  {"$arrayElemAt":
                   [
                       {"$split":
                        ["$TimeStamp",
                         ':'
                         ]
                        }, 0]
                   },
                  'minutes':
                  {"$arrayElemAt":
                   [
                       {"$split":
                        ["$TimeStamp", ':']
                        }, 1]
                   }
                  },
                 "sum_quantity":
                 {
                     "$sum":
                     "$Quantity"
                 },
                 "sum_total":
                 {
                     "$sum":
                     "$Total"
                 }
                 }
              },
             {"$project":
              {"_id": 1,
               "sum_quantity": 1,
               "sum_total": 1,
               "price":
               {"$divide":
                [
                    "$sum_total",
                    "$sum_quantity"
                ]
                }
               }
              },
             {"$sort": SON([("_id", -1)])
              },
             {"$limit": limits}
             ]
    else:
        pipeline =\
            [{"$match":
              {'TimeStamp':
               {"$lt":
                (datetime.strptime(todate,
                                   '%m/%d/%Y %I:%M %p'
                                   ) + timedelta(minutes=1)
                 ).strftime('%Y-%m-%dT%H:%M'),
                "$gte":
                datetime.strptime(fromdate,
                                  '%m/%d/%Y %I:%M %p'
                                  ).strftime('%Y-%m-%dT%H:%M')},
               'Pair': coin
               }
              },
             {"$group":
                {"_id":
                 {'datehours':
                  {"$arrayElemAt":
                   [
                       {"$split":
                        ["$TimeStamp",
                         ':'
                         ]
                        }, 0]
                   },
                  'minutes':
                  {"$arrayElemAt":
                   [
                       {"$split":
                        ["$TimeStamp", ':']
                        }, 1]
                   }
                  },
                 "sum_quantity":
                 {
                     "$sum":
                     "$Quantity"
                 },
                 "sum_total":
                 {
                     "$sum":
                     "$Total"
                 }
                 }
              },
             {"$project":
              {"_id": 1,
               "sum_quantity": 1,
               "sum_total": 1,
               "price":
               {"$divide":
                [
                    "$sum_total",
                    "$sum_quantity"
                ]
                }
               }
              },
             {"$sort": SON([("_id", -1)])
              }
             ]
    generator = list(collection.aggregate(pipeline))
    if generator:
        b = []
        for i in generator[::-1]:
            i['datetime'] = i['_id']['datehours'] + \
                ':' + i['_id']['minutes']
            if generator[::-1].index(i) == 0:
                b.append(i.copy())
                continue
            position = b.index(b[-1])
            difference = to_date(i['datetime']) -\
                to_date(b[position]['datetime'])
            if int(difference.total_seconds()) / 60 > 1:
                price = b[position]['price']
                base = to_date(i['datetime'])
                date_list = [
                    base - timedelta(minutes=x + 1)
                    for x in range(0, int(difference.total_seconds() / 60
                                          ) - 1)
                ][::-1]
                for d in date_list:
                    b.append({'datetime': to_string(d),
                              'price': price,
                              'sum_quantity': 0})
            b.append(i.copy())
        summarized = None
        if not fromdate:
            generator = b[::-1][:interval * 67][::interval]
            summarized = generator[:40]
            ema_basic_slow =\
                sum([Decimal(i['price']) for i in generator[41:]])\
                / Decimal(len(generator[41:]))
            ema_basic_fast =\
                sum([Decimal(i['price']) for i in generator[41:53]])\
                / Decimal(len(generator[41:53]))
        else:
            generator = b[::interval][::-1]
            summarized = generator
        alphafast = Decimal(2.0 / (1.0 + float(fast)))
        alphaslow = Decimal(2.0 / (1.0 + float(slow)))
        alphasignal = Decimal(2.0 / (1.0 + float(signal)))

        alphafast_1 = Decimal(1.0) - alphafast
        alphaslow_1 = Decimal(1.0) - alphaslow
        alphasignal_1 = Decimal(1.0) - alphasignal

        first_generation = []
        for m in summarized:
            data = {}
            data['pair'] = coin
            data['interval'] = '{}-Minute'.format(interval)
            data['datetime'] = m['datetime']
            data['date'] = m['datetime'].split('T')[0]
            data['time'] = m['datetime'].split('T')[1]
            data['price'] = Decimal(m['price'])
            data['volume'] = Decimal(m['sum_quantity'])
            data['ema_fast'] = alphafast * Decimal(data['price'])
            data['ema_slow'] = alphaslow * Decimal(data['price'])
            first_generation.append(data.copy())

        if not fromdate:
            first_generation.append(
                {'ema_fast': ema_basic_fast, 'ema_slow': ema_basic_slow})

        second_generation = []
        for g in first_generation[::-1]:
            position = first_generation[::-1].index(g)
            data = g.copy()
            if position > 0:
                data['ema_fast'] = data['ema_fast'] + alphafast_1 * \
                    second_generation[position - 1]['ema_fast']
                data['ema_slow'] = data['ema_slow'] + alphaslow_1 * \
                    second_generation[position - 1]['ema_slow']
            second_generation.append(data.copy())

        third_generation = []
        if not fromdate:
            indexation = 1
        else:
            indexation = 0
        for t in second_generation[indexation:]:
            data = t.copy()
            data['macd'] = data['ema_fast'] - data['ema_slow']
            data['signal_line'] = alphasignal * data['macd']
            third_generation.append(data.copy())

        fourth_generation = []
        for f in third_generation:
            position = third_generation.index(f)
            data = f.copy()
            if position > 0:
                data['signal_line'] = data['signal_line'] + alphasignal_1 * \
                    fourth_generation[position - 1]['signal_line']
            data['macd_hist'] = data['macd'] - data['signal_line']
            fourth_generation.append(data.copy())

        return fourth_generation[::-1]
    return False
