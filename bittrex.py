#!/usr/bin/python3
"""Scrapper for cryptocoins historical data."""
import csv
import logging
import traceback
from datetime import datetime
from time import sleep

import requests

from pymongo import MongoClient

# Logger configuration
logging.basicConfig(format='[%(asctime)s] %(levelname)s: %(message)s',
                    level=logging.INFO, datefmt='%Y/%m/%dT%H:%M:%S')

# MongoDB client configuration
client = MongoClient()
db = client.bittrex
collection = db.market

# User-defined configuration
coins_list =\
    ['TIX',
     'MER',
     'ADT',
     'MTL',
     'GRS',
     'ION',
     'VOX',
     'WINGS',
     'RISE',
     'RCN',
     'FCT',
     'GNT',
     'SALT',
     'XCP',
     'FUN',
     'ENG',
     'VRC',
     'BNT',
     'MONA',
     'BSD',
     'MEME',
     'DGD',
     'EDG',
     'VTC',
     'GUP',
     'STEEM',
     'SBD',
     'DNT',
     'GNO',
     'BLK']


def timing(data):
    """Convert user-defined filter into DB time."""
    return datetime.strptime(data,
                             '%m/%d/%Y %I:%M %p').strftime('%Y-%m-%dT%H:%M:%S')


def fetch(fromdate, todate, coin):
    """Save a DB query result into CSV file."""
    path = [timing(fromdate), timing(todate), coin]
    result = list(db.market.find(
        {'TimeStamp':
         {
             '$gt': path[0],
             '$lt': path[1]
         },
         'Pair': 'BTC-{}'.format(coin)
         }
    ).sort([('TimeStamp', -1)]))
    if not result:
        logging.critical('No results found!')
        return False
    logging.info('{} results found, writing to CSV...'.format(len(result)))
    filepath = '-'.join(path)
    with open('archive/{}.csv'.format(filepath), 'w') as dump:
        fieldnames = ['Id', 'Pair', 'TimeStamp', 'Quantity',
                      'Price', 'Total', 'FillType', 'OrderType']
        writer = csv.DictWriter(
            dump, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(result)
    return (filepath, result)


def write():
    """Create requests to the API and write data."""
    for c in coins_list:
        paired = 'BTC-{}'.format(c)
        logging.info('Parsing [{}]'.format(c))
        try:
            ops = [{**o, 'Pair': paired} for o in requests.get(
                   "https://bittrex.com/api/v1.1/public/" +
                   "getmarkethistory?market={}".format(paired)
                   ).json()['result']
                   ]
            logging.info('\tUpdating DB...')
            [collection.update_one(
             filter={'Id': i['Id'], 'Pair': i['Pair']},
             update={'$set': i},
             upsert=True
             ) for i in ops
             ]
            logging.info('\tDone!')
        except:
            traceback.print_exc()
            logging.warning('\tError parsing [{}]!'.format(c))
        sleep(1)


if __name__ == '__main__':
    write()
