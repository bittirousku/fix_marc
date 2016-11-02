# -*- coding: utf-8 -*-

"""
Fix incomplete arXiv records in INSPIRE.

The case when fixing is needed is when there is no 035 field (arxiv report_nr)
and 037__c is missing (primary arxiv category).

From:
    <datafield tag="035" ind1=" " ind2=" ">
        <subfield code="a">Gorkavyi:2016bcu</subfield>
        <subfield code="9">INSPIRETeX</subfield>
    </datafield>
    <datafield tag="037" ind1=" " ind2=" ">
        <subfield code="a">arXiv:1608.01541</subfield>
        <subfield code="9">arXiv</subfield>
    </datafield>
To:
    <datafield tag="035" ind1=" " ind2=" ">
        <subfield code="a">Gorkavyi:2016bcu</subfield>
        <subfield code="9">INSPIRETeX</subfield>
    </datafield>
    <datafield tag="035" ind1=" " ind2=" ">
        <subfield code="a">1608.01541</subfield>
        <subfield code="9">arXiv</subfield>
    </datafield>
    <datafield tag="037" ind1=" " ind2=" ">
        <subfield code="a">arXiv:1608.01541</subfield>
        <subfield code="c">gen-ph</subfield>
        <subfield code="9">arXiv</subfield>
    </datafield>


What this script does:

    * First gets all the inspire records with a given query
    (using module get_inspire_records)

    * Then parses the XML

    * For every record tries to find 037 field and extracts arxiv report_nr
      from it and adds the arxiv classification to it.

    * Tries to find 035 field and creates it if it does not exists with the
      information extracted from 037.

    * Finally writes a MARCXML record collection to one file.

Example usage:
    python fix_arxiv.py -p '037__9:arxiv - 037__c:**' -o 'tmp/from_inspire'
    python fix_arxiv.py -i 'tmp/from_inspire' -c 'tmp/correct'

Have fun.


"""
from __future__ import print_function

import getopt
import os
import sys

import requests
from furl import furl
from lxml import etree

from utils import (
    get_inspire_collections,
    marc_to_dict,
    write_corrected_marcxml,
)


def get_arxiv_report_nr(text):
    """Get arxiv report nr from a string."""
    return text.lower().lstrip("arxiv:").strip("/")

def get_arxiv_record(report_nr):
    """Query the arxiv OAI API with the report number. Return XML string."""
    arxiv_base_url = "http://export.arxiv.org/oai2"
    params = {
        "verb": "GetRecord",
        "identifier": "oai:arXiv.org:{}".format(report_nr),
        "metadataPrefix": "arXiv",
    }
    url = furl(arxiv_base_url).add(params).url
    print("Querying the arXiv API, report_nr " + report_nr)
    import time; time.sleep(5)
    arxiv_response = requests.get(url)
    if not arxiv_response.ok:
        # FIXME: there could be an exception
        return None

    return arxiv_response.content


def get_arxiv_category(report_nr):
    """Get the arxiv category from querying the arxiv API."""
    arxiv_record = etree.fromstring(get_arxiv_record(report_nr))
    categories_node = arxiv_record.xpath(
        "//*[local-name()='record']//*[local-name()='categories']"
    )
    if not categories_node:
        return None

    categories = categories_node[0].text
    primary_cat = categories.split()[0]

    return primary_cat.replace("physics:", "").strip()


def get_fixed_arxiv_marc_fields(record):
    """Check if MARC 035 and 037 fields need fixing and return them.

    035: check if the correct field already exists, and if not, create it.
    037: find the correct existing field, modify it and add it back to the list.
    """
    def pop_correct_marc_037(marc_037s):
        """Pop the correct 037 field for modifying."""
        new_marc_037 = {}
        for index, m37 in enumerate(marc_037s):
            m37 = m37["037"]
            if "a" in m37 and "9" in m37:
                if "arxiv" in m37["9"].lower():
                    new_marc_037 = marc_037s.pop(index)
                    return new_marc_037
        return new_marc_037

    def check_correct_marc_035_exists(marc_035s):
        """Check if the 035 field with arxiv report_nr exists already."""
        for index, m35 in enumerate(marc_035s):
            if "9" in m35["035"] and "arxiv" in m35["035"]["9"].lower():
                return True

    marc_035s = marc_to_dict(record, "035")
    marc_037s = marc_to_dict(record, "037")

    # Modify 037
    new_marc_037 = pop_correct_marc_037(marc_037s)
    report_no = get_arxiv_report_nr(new_marc_037["037"]["a"])
    if not report_no:
        import ipdb; ipdb.set_trace()
    try:
        new_marc_037["037"]["c"] = get_arxiv_category(report_no)
        print("arxiv category: " + new_marc_037["037"]["c"])
    except Exception as err:
        # manually intervene if something strange happens
        import ipdb; ipdb.set_trace()
    # FIXME: report_nr == arxiv:submit... check that this is fixed
    # FIXME: report_nr == '12012.zip' this doesn't exists in arxiv, just remove the report_nr
    marc_037s.append(new_marc_037)

    # Check if 035 exists and create it if necessary
    if not check_correct_marc_035_exists(marc_035s):
        new_marc_035 = {
            "035":
                {
                    "a": "oai:arXiv.org:{}".format(report_no),
                    "9": "arXiv",
                }
        }
        marc_035s.append(new_marc_035)


    # We can put them all in a single list:
    return marc_035s + marc_037s


def create_corrected_marcs(correct_outdir="", inspire_pattern="",
                           inspire_outdir="", indir=""):
    """Get all the necessary data and build the final MARC records here."""
    collections = []
    if inspire_outdir:
        collections = get_inspire_collections(
            inspire_pattern=inspire_pattern, inspire_outdir=inspire_outdir
        )
    elif indir:
        collections = get_inspire_collections(indir=indir)

    # Go through all the inspire xml records, find 035 and 037 fields,
    # process accordingly, and finally write new MARCXML files.
    # These files should later be uploaded with batchupload correct.
    fixed_records = []
    for collection in collections:
        for record in collection.xpath("//*[local-name()='record']"):
            recids = record.xpath("./*[local-name()='controlfield'][@tag='001']/text()")
            if recids:
                recid = recids[0]
            fixed_marc_record = get_fixed_arxiv_marc_fields(record)
            fixed_records.append((fixed_marc_record, recid))

    write_corrected_marcxml(fixed_records, correct_outdir)


def main(argv=None):
    """
    Parse arguments and try to get INSPIRE XML records for parsing, then
    try to fix the 773 fiels. Finally write new records to file.
    """
    if argv is None:
        argv = sys.argv

    inspire_outdir = ""
    correct_outdir = ""
    indir = ""
    inspire_pattern = ""

    helpshort = (
        "python fix_arxiv.py -p '037__9:arxiv - 037__c:**' [-o 'tmp/from_inspire'"
        "-c 'tmp/correct' -i 'tmp/from_inspire']"
    )

    # Parse arguments
    try:
        opts, _ = getopt.getopt(
            argv,
            "hp:o:c:i:",
            ["help", "pattern=", "inspire_outdir=", "correct_outdir=", "indir="]
        )
    except getopt.GetoptError as err:
        print(err)
        print(helpshort)
        sys.exit(2)
    for opt, arg in opts:
        if opt == "-h":
            print(helpshort)
            sys.exit()
        elif opt in ("-p", "--pattern"):
            inspire_pattern = arg
        elif opt in ("-o", "--inspire_outdir"):
            # For saving the fetched INSPIRE records
            inspire_outdir = os.path.join(arg, "")
        elif opt in ("-c", "--correct_outdir"):
            # For saving the corrected MARCXML
            correct_outdir = os.path.join(arg, "")
        elif opt in ("-i", "--indir"):
            # For using previously fetched and saved local files
            indir = os.path.join(arg, "")
    if not argv:
        print(helpshort)
        sys.exit()
    if not (inspire_pattern or indir):
        print(helpshort)
        print("\nPlease give INSPIRE search pattern or the path to local files")
        sys.exit()

    create_corrected_marcs(
        inspire_pattern=inspire_pattern,
        inspire_outdir=inspire_outdir,
        correct_outdir=correct_outdir,
        indir=indir
    )

if __name__ == "__main__":
    main(sys.argv[1:])
