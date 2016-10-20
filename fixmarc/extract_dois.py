# -*- coding: utf-8 -*-

"""Extract DOIs

This module will extract DOIs from a CSV file and output a file with a
list of DOIs (one per row).

USAGE:
input_file = "../tmp/input/isolde.csv"
new_dois = get_dois_not_in_inspire(input_file)
write_list_to_file(new_dois, outdir="../tmp/")

"""
from __future__ import absolute_import, print_function

import csv
import re
from tempfile import mkstemp

import requests

from get_inspire_records import fetch_records


def extract_dois(input_file):
    """Extract DOIs from a CSV file."""
    with open(input_file) as csvfile:
        reader = csv.DictReader(csvfile, delimiter="\t")
        records = []
        for record in reader:
            # records.append(record) # If you want the whole record
            # records.append({"DOI": record["DOI"], "Reference": record["Reference"]})
            # take only DOI and reference columns and put them in a list,
            # we don't care about order or anything
            records.append(record["DOI"])
            records.append(record["Reference"])

    # Now we have a big list with all the raw data, let's find the DOIs
    dois = []
    for line in records:
        doi_search_result = re.search(r'(\d{2}\.\d{4}.*/.*)', line)
        # This should find them all, no need to check for DOI: or doi.dx.org/
        if doi_search_result:
            doi = doi_search_result.group(1).split(" ", 1)[0]
            doi = clean_text(doi)
            dois.append(doi)

    return set(dois)


def clean_text(text):
    """Do some cleaning on a string."""
    text = text.rstrip(">")
    text = text.rstrip(".")
    text = text.rstrip(",")
    text = text.replace("\xc2\xa0", "")
    text = text.split("/meta")[0]

    return text


def test_valid_doi(doi):
    """Test that the string is a valid DOI."""
    # FIXME: here come some strange errors:
    # requests.exceptions.ConnectionError: ('Connection aborted.',
    # BadStatusLine("''",))
    req = requests.post(url="http://www.dx.doi.org/", data={"hdl": doi})
    if req.status_code == 200:
        return True
    else:
        print(doi + " is not a valid DOI!")
        return False


def check_doi_in_inspire(doi):
    """Check if we have a record with a certain DOI in INSPIRE already."""
    return bool(
        fetch_records(
            inspire_pattern="doi:" + doi,
            list_size=10
        )
    )


def get_dois_not_in_inspire(input_file):
    """Return DOIs that are not in INSPIRE yet."""
    dois = extract_dois(input_file)
    new_dois = []
    for doi in dois:
        if not check_doi_in_inspire(doi):
            # import time; time.sleep(10)  # Don't annoy dx.doi.org too much
            # if test_valid_doi(doi):
            new_dois.append(doi)

    return new_dois


def write_list_to_file(list_of_text, outdir="/tmp/"):
    """Write a list of text to a file."""
    _, outfile = mkstemp(prefix="new_dois_", dir=outdir, suffix=".txt")
    with open(outfile, "w") as filee:
        for line in list_of_text:
            filee.write(line + "\n")
    print("Wrote " + str(len(list_of_text)) + " new DOIs to file " + outfile)
