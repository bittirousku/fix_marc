# -*- coding: utf-8 -*-

"""
Get all the Inspire records for a given query.

The query will break the full list down to `list_size` (e.g. 50 or 250)
records per file. The search can be continued with keyword `jrec`.
All the results are kept on separate files. Result format is MARCXML.

"""

import os
import sys
import re
import getopt

from tempfile import mkdtemp, mkstemp

from invenio_client import InvenioConnector
import getpass
import logging

from lxml import etree



def fetch_records(outdir, inspire_pattern, list_size):
    """Get records from Inspire with InvenioConnector and write to file."""
    if not os.path.exists(outdir):
        os.makedirs(outdir)
    files_created = []

    if "*" in inspire_pattern:
        # Have to add `wl=0` to make wildcards function properly.
        # This requires authentication.
        uname = raw_input("Inspire login: ")
        pword = getpass.getpass()
        inspire = InvenioConnector(
            "https://inspirehep.net",
            user=uname,
            password=pword
            )
    else:
        inspire = InvenioConnector("https://inspirehep.net")

    records = inspire.search(
        p=inspire_pattern,
        of="xm",
        rg=list_size,
        wl=0
        )

    n_records = get_number_of_records_in_batch(records)
    total_amount = get_total_number_of_records(records)
    if not total_amount:
        print("No records found.")
        sys.exit()
    print("Total amount of results: " + total_amount)

    _, outfile = mkstemp(prefix="records1" + "_", dir=outdir, suffix=".xml")

    with open(outfile, "w") as f:
        f.write(records)
    startpoint = list_size + 1
    print("Wrote " + str(n_records) + " records to file " + outfile)
    files_created.append(outfile)

    while startpoint < int(total_amount):
        # XML files of `list_size` records will be written to directory "inspire_xmls/".
        # total_amount is the total number of search results.
        records = inspire.search(
            p=inspire_pattern,
            of="xm",
            rg=list_size,
            jrec=startpoint,
            wl=0)

        n_records = get_number_of_records_in_batch(records)
        _, outfile = mkstemp(prefix="records" + str(startpoint) + "_", dir=outdir, suffix=".xml")

        with open(outfile, "w") as f:
            f.write(records)
        startpoint += list_size + 1
        print("Wrote " + str(n_records) + " records to file " + outfile)
        files_created.append(outfile)

    return files_created


def get_number_of_records_in_batch(records_string):
    """Get the number of record nodes in a XML string."""
    collection = etree.fromstring(records_string)
    return len(collection.xpath("//*[local-name()='record']"))

def get_total_number_of_records(records_string):
    """Get the total number of search results."""
    collection = etree.fromstring(records_string)
    for comment in collection.xpath("//comment()"):
        if "Search-Engine-Total-Number-Of-Results" in comment.text:
            tot_num = re.search(r'.?Results:\s(\d+).?', comment.text).group(1)
            return tot_num

def main(argv=None):
    """
    You have to input inspire search pattern or path to file of recids.
    Optional arguments are output directory and size of one result page.
    """
    if argv is None:
        argv = sys.argv

    outdir = "inspire_xmls/"
    list_size = 50
    inspire_pattern = ""
    helptext = 'USAGE: \n\t python get_inspire_records.py -p <pattern> [-o <outdir> -r <recid_file>]'

    #parse search pattern and optional output dir from the arguments
    try:
        opts, args = getopt.getopt(argv,
                                   "ho:p:r:l:",
                                   ["outdir=", "pattern=", "recid_file=", "list_size="]
        )
    except getopt.GetoptError:
        print(helptext)
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print(helptext)
            sys.exit()
        elif opt in ("-o", "--ofile"):
            outdir = os.path.join(arg, '')
            #argv = argv[2:]
        elif opt in ("-l", "--list_size"):
            list_size = arg # should be int
        elif opt in ("-p", "--pattern"):
            inspire_pattern = arg
        elif opt in ("-r", "--recid_file"):
            with open(arg, "r") as f: recids = f.read().split()
            if recids:
                inspire_pattern = "recid " + " or ".join(recids)
    if not argv:
        print(helptext)
        sys.exit()
    if not inspire_pattern:
        print("Search pattern is required.")
        sys.exit(2)
    print('Output dir is ' + outdir)
    print("Inspire search pattern: " + inspire_pattern)

    # TEST pattern:
    #inspire_pattern = 'tc proceedings and 773__p:Nucl.Instrum.Meth.'
    fetch_records(outdir, inspire_pattern, list_size)


if __name__ == "__main__":
    main(sys.argv[1:])
