# -*- coding: utf-8 -*-
from __future__ import print_function

import os


from tempfile import mkstemp

from lxml import etree

from get_inspire_records import fetch_records

from utils import (
    get_inspire_collections,
    marc_to_dict,
    write_corrected_marcxml,
)

recids_with_problems = [
    1474840, 1397051, 1384910, 1374332, 1358160, 1332846, 1415326, 1357252, 1312933, 1245045, 1242687, 1242140, 1241567, 1277137, 1218997, 1208984, 1207641, 1206589, 1189273, 1119706]

collections = get_inspire_collections(indir="../tmp/fix_previous_correct")


collection = collections[0]
fixed_records = []

for record in collection.xpath("//*[local-name()='record']"):
    # if two 035s, remove the other one and proceed
    recids = record.xpath("./*[local-name()='controlfield'][@tag='001']/text()")
    if recids:
        recid = recids[0]
    if int(recid) in recids_with_problems:
        marc_035s = marc_to_dict(record, "035")
        marc_037s = marc_to_dict(record, "037")
        seen_arxiv = False
        for index, m35 in enumerate(marc_035s):
            if "arxiv" in m35["035"]["9"].lower():
                if seen_arxiv:
                    marc_035s.pop(index)
                seen_arxiv = True

        fixed_record = marc_035s + marc_037s
        fixed_records.append((fixed_record, recid))


correct_outdir = "/tmp"
write_corrected_marcxml(fixed_records, correct_outdir)
