#!/usr/bin/env python

"""
This is a simple script to print out potentially redundant indexes in a mongdb instance.
For example, if an index is defined on {field1:1,field2:1} and there is another index
with just fields {field1:1}, the latter index is not needed since the first index already
indexes the necessary fields.
"""
from pymongo import Connection
from pymongo import ReadPreference
from argparse import ArgumentParser

def main():
    description = 'Print out potentially redundant indexes in a MongoDB instance.'

    global options
    parser = ArgumentParser(description=description)
    parser.add_argument('-H', '--host', default='localhost',
      help="mongodb host, e.g. 'api.foo.com' default to 'localhost' if not specified")
    parser.add_argument('-P', '--port', type=int, default=27017, 
      help="mongodb port if not the default 27017")
    args = parser.parse_args()

    connection = Connection(host=args.host,
            port=args.port,
            read_preference=ReadPreference.SECONDARY)

    def compute_signature(index):
        signature = index["ns"]
        for key in index["key"]:
            try:
                signature += "%s_%s" % (key, int(index["key"][key]))
            except ValueError:
                signature += "%s_%s" % (key, index["key"][key])
        return signature

    def report_redundant_indexes(current_db):
        print "Checking DB: %s" % current_db.name
        indexes = current_db.system.indexes.find()
        index_map = {}
        for index in indexes:
            signature = compute_signature(index)
            index_map[signature] = index

        for signature in index_map.keys():
            for other_sig in index_map.keys():
                if signature == other_sig:
                    continue
                if other_sig.startswith(signature):
                    print "Index %s[%s] may be redundant with %s[%s]" % (
                        index_map[signature]["ns"],
                        index_map[signature]["name"],
                        index_map[other_sig]["ns"],
                        index_map[other_sig]["name"])

    for db in connection.database_names():
        report_redundant_indexes(connection[db])

if __name__ == "__main__":
    main()
