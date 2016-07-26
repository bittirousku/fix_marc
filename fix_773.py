# -*- coding: utf-8 -*-

"""
This script tries to fix 773 fieds in INSPIRE records.
The case when fixing is needed is when 773 has x subfield with pubinfo (with wrong name),
but is missing other subfields.

From:
    <datafield tag="773" ind1=" " ind2=" ">
        <subfield code="w">C09-05-13</subfield>
        <subfield code="t">Prepared for</subfield>
        <subfield code="x">Nucl. Instrum. Methods A630 (2011) 1-319</subfield>
        <subfield code="c">1-319</subfield>
    </datafield>
To:
    <datafield tag="773" ind1=" " ind2=" ">
        <subfield code="c">pp. 1-319</subfield>
        <subfield code="p">Nucl.Instrum.Meth.</subfield>
        <subfield code="v">A630</subfield>
        <subfield code="w">C09-05-13</subfield>
        <subfield code="y">2011</subfield>
    </datafield>


What this script does:

    * First gets all the inspire records with a given query
    (using module get_inspire_records)

    * Then parses the XML

    * Takes the 773 field

    * Extracts information from 773__x

    * Inserts the extracted information back into 773

    * Writes a file of MARCXML records to be sent to batchupload correction.

Example usage:
    python fix_773.py -c 'Nucl.Instrum.Meth.' -w 'Nucl. Instrum. Methods' -p 'tc proceedings and 773__x:"Nucl. Instrum. methods a*" and not 773__p:Nucl.Instrum.Meth.'

    python fix_773.py -c 'Nucl.Instrum.Meth.' -w 'Nucl. Instrum. Methods' -p 'tc proceedings and 773__x:"Nucl. Instrum. methods a*" and not 773__p:Nucl.Instrum.Meth.' -o "inspire_xmls"

    python fix_773.py -c 'Nucl.Instrum.Meth.' -w 'Nucl. Instrum. Methods' -i "../tmp/inspire_xmls"




Have fun.

NOTE: At the moment this works specially with Proceedings records:
'pp' is added before page ranges.
NOTE: This also assumes the title in pubinfo is wrong.

"""
from __future__ import print_function

import os
import sys

import getopt

import re

from tempfile import mkstemp

from lxml import etree

from get_inspire_records import fetch_records
from utils import (
    get_inspire_collections,
    marc_to_dict,
    load_xml_strings,
    load_xml_files,
    write_corrected_marcxml,
)


def find_local_files(directory):
    """Return the contents of a directory."""
    return [os.path.join(directory, f) for f in os.listdir(directory)]

def split_773__x(marc_773, wrong_xname, search_pattern, correct_name):
    """Extract information from MARC 773__x."""
    xfield = marc_773.pop("x", "")
    # Let's do some cleaning
    xfield = xfield.replace(",", "")
    xfield = xfield.replace("pp.", "")
    if wrong_xname in xfield:
        vol, year, pagerange = search_pattern.search(xfield).groups()
        pagerange = "pp." + pagerange
        marc_773["c"] = pagerange
        marc_773["v"] = vol
        marc_773["y"] = year.strip("()")
        marc_773["p"] = correct_name

    return marc_773


def create_corrected_marcs(wrong_xname, correct_name, correct_outdir="",
                           inspire_pattern="", inspire_outdir="", indir=""):
    """Get all the necessary data and build the final MARC records here."""
    # Prepare a regex pattern for finding the wrong name from 773_x
    wrong_xname = wrong_xname.rstrip(".")
    wrong_name_pattern = re.compile(wrong_xname + r'\s(.*)\s\((\d*)\)\s(\w+-\w+).*')

    collections = []
    if inspire_outdir:
        collections = get_inspire_collections(inspire_pattern=inspire_pattern, outdir=inspire_outdir)
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
            marc_773s = marc_to_dict(record, "773")
            for m773 in marc_773s:
                # NOTE: assuming only one 773 field!
                if "x" in m773["773"]:
                    m773 = split_773__x(
                        m773, wrong_xname, wrong_name_pattern, correct_name)
                    fixed_records.append(([m773], recid))

    write_corrected_marcxml(fixed_records, correct_outdir)


def main(argv=None):
    """
    Parse arguments and try to get INSPIRE XML records for parsing, then
    try to fix the 773 fiels. Finally write new records to file.
    """
    if argv is None:
        argv = sys.argv

    inspire_outdir = ''
    correct_outdir = ''
    indir = ''
    correct_name = ''
    wrong_xname = ''
    inspire_pattern = ''


    helpshort = (
        'USAGE: python fix_773.py -c <correct_name> '
        '-w <wrong_name> [-p <pattern> -o <inspire_outdir> -x <correct_outdir> -i <indir>]\n\n'
        'For more help use --morehelp'
    )

    helplong = (
        'USAGE: python fix_773.py -c <correct_name> '
        '-w <wrong_name> [-p <pattern> -o <inspire_outdir> -x <correct_outdir> -i <indir>]\n\n'

        'Mandatory arguments:\n'
        '  {:<25}'.format("-c --correct_name") + "the correct name, e.g. \'Nucl.Instrum.Meth.\'\n" +
        '  {:<25}'.format("-w --wrong_name") +
        "the current wrong name in 773__x you want to change, e.g. \'Nucl. Instrum. Methods\'\n\n" +

        'Choose one of these two: \n'
        '  {:<25}'.format("-p --pattern") +
        "INSPIRE search pattern, e.g. \'tc proceedings and 773__x:\"Nucl. Instrum. methods a*\"\'\n" +
        '  {:<25}'.format("-i --indir") +
        "input directory where the previously fetched INSPIRE records are, e.g., \'inspire_xmls'\n\n" +

        'Optional:\n'
        '  {:<25}'.format("-i --inspire_outdir") +
        "output directory if you want to save the queried INSPIRE XMLs locally, default: \'inspire_xmls'\n" +
        '  {:<25}'.format("-x --correct_outdir") +
        "output directory where you want to save the newly created XML files, default: \'correct'\n"
    )

    # Parse arguments
    try:
        opts, _ = getopt.getopt(
            argv,
            "hmc:w:p:o:x:i:",
            ["help", "morehelp", "correct_name=", "wrong_name=", "pattern=",
             "inspire_outdir=", "correct_outdir=", "indir="]
            )
    except getopt.GetoptError as err:
        print(err)
        print(helpshort)
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print(helpshort)
            sys.exit()
        elif opt == '--morehelp':
            print(helplong)
            sys.exit()
        elif opt in ("-c", "--correct_name"):
            correct_name = arg
        elif opt in ("-w", "--wrong_name"):
            wrong_xname = arg
        elif opt in ("-p", "--pattern"):
            inspire_pattern = arg
        elif opt in ("-o", "--inspire_outdir"):
            # For saving the fetched INSPIRE records
            inspire_outdir = os.path.join(arg, '')
        elif opt in ("-x", "--correct_outdir"):
            # For saving the corrected MARCXML
            correct_outdir = os.path.join(arg, '')
        elif opt in ("-i", "--indir"):
            # For using previously fetched and saved local files
            indir = os.path.join(arg, '')
    if not argv:
        print(helpshort)
        sys.exit()
    if not (correct_name and wrong_xname):
        print(helpshort)
        print("\nPlease give the correct name and the name to be fixed.")
        sys.exit()
    if not (inspire_pattern or indir):
        print(helpshort)
        print("\nPlease give INSPIRE search pattern or the path to local files")
        sys.exit()

    create_corrected_marcs(
        wrong_xname,
        correct_name,
        inspire_pattern=inspire_pattern,
        inspire_outdir=inspire_outdir,
        correct_outdir=correct_outdir,
        indir=indir
    )


if __name__ == "__main__":
    main(sys.argv[1:])
