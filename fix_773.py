# -*- coding: utf-8 -*-

"""

First get all the inspire records with a given query (use module get_inspire_records)

Then parse the XML

Take 773 field

Split the pubinfo in subfield x

Create new marc773

Remember to add pp. in page numbers!

Write XML files for submitting for correction.

"""
import os

from lxml import etree

import get_inspire_records

from get_inspire_records import fetch_records




def load_xml_files(inspire_xmls):
    """Load the xml files to etree objects."""
    # QUESTION: Would it be better to just load the records directly to memory and
    # not save to file?
    collections = []
    for xml_file in inspire_xmls:
        with open(xml_file, "r") as f:
            collections.append(etree.parse(f))
    return collections


def marc_to_dict(node, tag):
    """Convert a MARCXML node to a dictionary."""
    marcdict = {}
    marc_node = node.xpath("./*[local-name()='datafield'][@tag='"+ tag +"']")
    subfields = marc_node[0].xpath("./*[local-name()='subfield']")
    for subfield in subfields:
        dkey = subfield.xpath("@code")[0]
        dvalue = subfield.xpath("text()")[0]  # FIXME these [0]s might cause trouble
        marcdict[dkey] = dvalue

    return marcdict

def load_local_files(d):
    """Return the contents of a directory."""
    return [os.path.join(d, f) for f in os.listdir(d)]

def split_773__x(marc_773):
    """Extract information from MARC 773__x."""
    # TODO: should be able to modify the parameters here somehow.
    import ipdb; ipdb.set_trace()
    pass
    #return new_marc_773


def write_to_file(marc_773):
    # TODO: this should do the same as hepcrawl XMLWriterPipeLine
    pass

#inspire_xmls = fetch_records("temppi", "tc proceedings and 773__p:Nucl.Instrum.Meth.", 50)
inspire_xmls = load_local_files("temppi")  # to not to fetch new files all the time
collections = load_xml_files(inspire_xmls)
collection = collections[0]

for record in collection.xpath("//*[local-name()='record']"):
    marc_773 = marc_to_dict(record, "773")
    if "x" in marc_773:
        marc_773 = split_773__x(marc_773)
        #write_to_file()





#<datafield tag="773" ind1=" " ind2=" ">
    #<subfield code="c">04001</subfield>
    #<subfield code="p">EPJ Web Conf.</subfield>
    #<subfield code="v">95</subfield>
    #<subfield code="x">EPJ Web Conf. 95 (2015) 04001</subfield>
    #<subfield code="y">2015</subfield>
