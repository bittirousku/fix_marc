# -*- coding: utf-8 -*-
from __future__ import print_function

import os


from tempfile import mkstemp

from lxml import etree

from get_inspire_records import fetch_records


def load_xml_files(inspire_xml_paths):
    """Load existing XML files to etree objects."""
    collections = []
    for xml_file in inspire_xml_paths:
        with open(xml_file, "r") as f:
            collections.append(etree.parse(f))
    return collections


def load_xml_strings(inspire_xml_strings):
    """Load XML strings to etree objects."""
    collections = []
    for collection in inspire_xml_strings:
        collections.append(etree.fromstring(collection))
    return collections


def marc_to_dict(node, tag):
    """Convert MARCXML nodes with a given code to a list of dictionaries."""
    marc_nodes = node.xpath("./*[local-name()='datafield'][@tag='"+ tag +"']")
    marc_dicts = []
    for node in marc_nodes:
        marcdict = {}
        subfields = node.xpath("./*[local-name()='subfield']")
        for subfield in subfields:
            try:
                # There might be empty subfields
                dkey = subfield.xpath("@code")[0]
                dvalue = subfield.xpath("text()")[0]
            except IndexError:
                continue
            marcdict[dkey] = dvalue
        marc_dicts.append({tag: marcdict})

    return marc_dicts

def find_local_files(directory):
    """Return the contents of a directory."""
    return [os.path.join(directory, f) for f in os.listdir(directory)]


def get_inspire_collections(inspire_pattern=None, inspire_outdir=None, indir=None):
    """Get the Inspire record collections. One per XML file."""
    collections = []
    if inspire_outdir:
        # Fetch and save to disk
        inspire_xml_paths = fetch_records(inspire_pattern, 50, outdir=inspire_outdir)
        collections = load_xml_files(inspire_xml_paths)
    elif indir:
        # Load the previously saved files
        inspire_xml_paths = find_local_files(indir)
        collections = load_xml_files(inspire_xml_paths)

    return collections


def write_corrected_marcxml(fixed_records, correct_outdir, recid=None):
    """Write corrected MARC fields to a MARCXML file."""
    if not correct_outdir:
        correct_outdir = "/tmp/"
    if not os.path.exists(correct_outdir):
        os.makedirs(correct_outdir)

    _, outfile = mkstemp(prefix="correct" + "_",
                         dir=correct_outdir,
                         suffix=".xml")
    with open(outfile, "w") as f:
        line = '<collection>\n'
        for record, recid in fixed_records:
            line += '<record>\n'
            if recid:
                line += '  <controlfield tag="001">{}</controlfield>\n'.format(recid)
            for marcfield in record:
                marctag = marcfield.keys()[0]
                line += '  <datafield tag="{}" ind1=" " ind2=" ">\n'.format(marctag)
                for code in sorted(marcfield[marctag]):
                    line += '    <subfield code="{}">{}</subfield>\n'.format(code, marcfield[marctag][code])
                line += '  </datafield>\n'
            line += '</record>\n'
        line += '</collection>\n'
        f.write(line)

    no_of_records = len(fixed_records)
    print("Wrote " + str(no_of_records) + " correct records to file " + outfile)
