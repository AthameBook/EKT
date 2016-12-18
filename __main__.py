#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is based on ExtractCoverThumbs, licensed under
# GNU Affero GPLv3 or later.
# Copyright © Robert Błaut.

from __future__ import print_function

__appname__ = u'ExtraKindleTools'

import argparse
import os
import sys
from lib.cleaner import Cleaner
from lib.extract_cover_thumbs import extract_cover_thumbs
from distutils.util import strtobool

parser = argparse.ArgumentParser()
parser.add_argument('-V', '--version', action='version',
                    version="1.0.0")
parser.add_argument("kindle_directory", help="directory where is a Kindle"
                    " Paperwhite mounted")
parser.add_argument("-s", "--silent", help="print less informations",
                    action="store_true")
parser.add_argument("--overwrite-pdoc-thumbs",
                    help="overwrite personal documents (PDOC) cover "
                         "thumbnails",
                    action="store_true")
parser.add_argument("--overwrite-amzn-thumbs",
                    help="overwrite amzn ebook (EBOK) and book sample (EBSP)"
                         " cover thumbnails",
                    action="store_true")
parser.add_argument("-o", "--overwrite-apnx", help="overwrite APNX files",
                    action="store_true")
parser.add_argument("--skip-apnx", help="skip generating APNX files",
                    action="store_true")
parser.add_argument("--patch-azw3",
                    help="change PDOC to EBOK in AZW3 files (experimental)",
                    action="store_true")
parser.add_argument("-z", "--azw", help="process also AZW files",
                    action="store_true")
parser.add_argument('-d', '--days', nargs='?', metavar='DAYS', const='7',
                    help='only "younger" ebooks than specified DAYS will '
                    'be processed (default: 7 days).')
parser.add_argument("--mark-real-pages",
                    help="mark computed pages as real pages "
                    "(only with -l and -d)",
                    action="store_true")

args = parser.parse_args()

kindlepath = args.kindle_directory
docs = os.path.join(kindlepath, 'documents')

def user_yes_no_query(question):
    sys.stdout.write('%s [y/n]\n' % question)
    while True:
        try:
            return strtobool(raw_input().lower())
        except ValueError:
            sys.stdout.write('Please respond with \'y\' or \'n\'.\n')

if __name__ == '__main__':
    Cleaner(kindlepath)
    extract_cover_thumbs(args.silent, args.overwrite_pdoc_thumbs,
                         args.overwrite_amzn_thumbs,
                         args.overwrite_apnx, args.skip_apnx,
                         kindlepath, args.azw, args.days)
