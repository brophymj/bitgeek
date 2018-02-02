#!/usr/bin/python3
"""Helpers func for Bittrex Flask app."""
from datetime import datetime, timedelta
from decimal import Decimal

from bson.son import SON
from pymongo import MongoClient

connection = MongoClient()
db = connection.bittrex
collection = db.market


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


def summarize(interval, todate, coin, fast, slow, signal):
    """Get the graph generated."""
    limits = interval * 40
    coin = 'BTC-' + coin
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
    summarized = list(collection.aggregate(pipeline))
    if summarized:
        alphafast = Decimal(2.0 / (1.0 + float(fast)))
        alphaslow = Decimal(2.0 / (1.0 + float(slow)))
        alphasignal = Decimal(2.0 / (1.0 + float(signal)))

        alphafast_1 = Decimal(1.0) - alphafast
        alphaslow_1 = Decimal(1.0) - alphaslow
        alphasignal_1 = Decimal(1.0) - alphasignal

        first_generation = []
        for m in summarized:
            data = {}
            data['datetime'] = m['_id']['datehours'] + \
                ':' + m['_id']['minutes']
            data['price'] = Decimal(m['price'])
            data['volume'] = Decimal(m['sum_quantity'])
            data['ema_fast'] = alphafast * Decimal(data['price'])
            data['ema_slow'] = alphaslow * Decimal(data['price'])
            first_generation.append(data.copy())

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
        for t in second_generation:
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
