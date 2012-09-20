#!/usr/bin/env python

"""
This script prints some basic collection stats about the size of the
collections and their indexes.
"""

from prettytable import PrettyTable
import psutil
from pymongo import Connection
from pymongo import ReadPreference
from argparse import ArgumentParser
import os

MongoHost = 'localhost'
MongoPort = 27017
MongoUser = None
MongoPassword = None

def compute_signature(index):
    signature = index["ns"]
    for key in index["key"]:
        signature += "%s_%s" % (key, index["key"][key])
    return signature

def get_collection_stats(database, collection):
    print "Checking DB: %s" % collection.full_name
    return database.command("collstats", collection.name)

# From http://www.5dollarwhitebox.org/drupal/node/84
def convert_bytes(bytes):
    bytes = float(bytes)
    if bytes >= 1099511627776:
        terabytes = bytes / 1099511627776
        size = '%.2fT' % terabytes
    elif bytes >= 1073741824:
        gigabytes = bytes / 1073741824
        size = '%.2fG' % gigabytes
    elif bytes >= 1048576:
        megabytes = bytes / 1048576
        size = '%.2fM' % megabytes
    elif bytes >= 1024:
        kilobytes = bytes / 1024
        size = '%.2fK' % kilobytes
    else:
        size = '%.2fb' % bytes
    return size

def main():
    global MongoHost, MongoPort, MongoUser, MongoPassword

    usage = 'Usage: %prog [options]'
    description = 'Generate index statistics for all collections in all DBs in HOST MongoDB'

    global options
    parser = ArgumentParser(description=description)
    parser.add_argument('-H', '--host',
      help="mongodb host, e.g. 'api.foo.com' default to 'localhost' if not specified")
    parser.add_argument('-P', '--port', type=int, default=27017, 
      help="mongodb port if not the default 27017")
    parser.add_argument('-p', '--password',
      help="the account password")
    parser.add_argument('-u', '--username',
      help="user account to use with MongoDB")
    args = parser.parse_args()

    if (args.host is None
        and args.port is None):
      parser.print_help()
      return

    if (args.host is not None):
        MongoHost = args.host
    if (args.port is not None):
        MongoPort = args.port
    connection = Connection(host=MongoHost,
            port=MongoPort,
            read_preference=ReadPreference.SECONDARY)

    summary_stats = {
        "count" : 0,
        "size" : 0,
        "indexSize" : 0
    }
    all_stats = []

    all_db_stats = {}
    for db in connection.database_names():
        # FIXME: Add an option to include oplog stats.
        if db == "local":
            continue

        database = connection[db]
        all_db_stats[database.name] = []
        for collection_name in database.collection_names():
            stats = get_collection_stats(database, database[collection_name])
            all_stats.append(stats)
            all_db_stats[database.name].append(stats)

            summary_stats["count"] += stats["count"]
            summary_stats["size"] += stats["size"]
            summary_stats["indexSize"] += stats.get("totalIndexSize", 0)

    x = PrettyTable()
    x._set_field_names(["Collection", "Index","% Size", "Index Size"])
    x.align["Collection"] = "l"
    x.align["Index"] = "l"
    x.align["% Size"] = "r"
    x.align["Index Size"] = "r"
    x._set_padding_width(1)

    print

    index_size_mapping = {}
    for db in all_db_stats:
        db_stats = all_db_stats[db]
        count = 0
        for stat in db_stats:
            count += stat["count"]
            for index in stat["indexSizes"]:
                index_size = stat["indexSizes"].get(index, 0)
                row = [stat["ns"], index,
                          "%0.1f%%" % ((index_size / float(summary_stats["indexSize"])) * 100),
                  convert_bytes(index_size)]
                index_size_mapping[index_size] = row
                x.add_row(row)


    print "Index Overview"
    x.sortby = "Collection"
    print(x)

    print
    print "Top 5 Largest Indexes"
    x = PrettyTable()
    x._set_field_names(["Collection", "Index","% Size", "Index Size"])
    x.align["Collection"] = "l"
    x.align["Index"] = "l"
    x.align["% Size"] = "r"
    x.align["Index Size"] = "r"
    x._set_padding_width(1)

    top_five_indexes = sorted(index_size_mapping.keys(), reverse=True)[0:5]
    for size in top_five_indexes:
        x.add_row(index_size_mapping.get(size))
    print(x)
    print

    print "Total Documents:", summary_stats["count"]
    print "Total Data Size:", convert_bytes(summary_stats["size"])
    print "Total Index Size:", convert_bytes(summary_stats["indexSize"])

    ram_headroom = psutil.phymem_usage()[0] - summary_stats["indexSize"]
    print "RAM Headroom:", convert_bytes(ram_headroom)
    print "Available RAM Headroom:", convert_bytes((100 - psutil.phymem_usage()[3]) / 100 * ram_headroom)

if __name__ == "__main__":
    main()
