#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Based on ExtractCoverThumbs, licensed under
# GNU Affero GPLv3 or later.
# Copyright © Robert Błaut.
#

from __future__ import print_function
import sys
import os

from imghdr import what
from io import BytesIO
from datetime import datetime

import kindle_unpack
from lib.apnx import APNXBuilder
from lib.pages import find_exth
from lib.pages import get_pages
from lib.kfxmeta import get_kindle_kfx_metadata
from lib.dualmetafix import DualMobiMetaFix

SFENC = sys.getfilesystemencoding()

def get_cover_image(section, mh, metadata, doctype, file, fide, is_verbose):
    try:
        cover_offset = metadata['CoverOffset'][0]
    except KeyError:
        return False
    beg = mh.firstresource
    end = section.num_sections
    imgnames = []
    for i in range(beg, end):
        data = section.load_section(i)
        tmptype = data[0:4]
        if tmptype in ["FLIS", "FCIS", "FDST", "DATP", "SRCS", "CMET",
                       "FONT", "RESC"]:
            imgnames.append(None)
            continue
        if data == chr(0xe9) + chr(0x8e) + "\r\n":
            imgnames.append(None)
            continue
        imgtype = what(None, data)
        if imgtype is None and data[0:2] == b'\xFF\xD8':
            last = len(data)
            while data[last - 1:last] == b'\x00':
                last -= 1
            if data[last - 2:last] == b'\xFF\xD9':
                imgtype = "jpeg"
        if imgtype is None:
            imgnames.append(None)
        else:
            imgnames.append(i)
        if len(imgnames) - 1 == int(cover_offset):
            return data
    return False

def generate_apnx_files(docs, is_overwrite_apnx, days):
    apnx_builder = APNXBuilder()
    if days is not None:
        dtt = datetime.today()
        days_int = int(days)
    else:
        days_int = 0
        diff = 0
    for root, dirs, files in os.walk(docs):
        for name in files:
            if 'documents' + os.path.sep + 'dictionaries' in root:
                continue
            if '.sdr' in root:
                continue
            if days is not None:
                try:
                    dt = os.path.getctime(mobi_path)
                except OSError:
                    continue
                dt = datetime.fromtimestamp(dt).strftime('%Y-%m-%d')
                dt = datetime.strptime(dt, '%Y-%m-%d')
                diff = (dtt - dt).days
            if name.lower().endswith(('.azw3', '.mobi', '.azw')) and diff <= days_int:
                sdr_dir = os.path.join(root, os.path.splitext(
                                       name)[0] + '.sdr')
                if not os.path.isdir(sdr_dir):
                    os.makedirs(sdr_dir)
                apnx_path = os.path.join(sdr_dir, os.path.splitext(
                                         name)[0] + '.apnx')
                if not os.path.isfile(apnx_path) or is_overwrite_apnx:
                    if '!DeviceUpgradeLetter!' in name:
                        continue
                    apnx_builder.write_apnx(mobi_path, apnx_path)

def extract_cover_thumbs(is_silent, is_overwrite_pdoc_thumbs,
                         is_overwrite_amzn_thumbs, is_overwrite_apnx,
                         skip_apnx, kindlepath, is_azw, days):
    docs = os.path.join(kindlepath, 'documents')
    is_verbose = not is_silent
    if days is not None:
        dtt = datetime.today()
        days_int = int(days)
    else:
        days_int = 0
        diff = 0

    if not os.path.isdir(os.path.join(kindlepath, 'system', 'thumbnails')):
        return 1
    if is_azw:
        extensions = ('.azw', '.azw3', '.mobi', '.kfx', '.azw8')
    else:
        extensions = ('.azw3', '.mobi', '.kfx', '.azw8')
    for root, dirs, files in os.walk(docs):
        for name in files:
            if 'documents' + os.path.sep + 'dictionaries' in root:
                continue
            if '.sdr' in root:
                continue
            if days is not None:
                try:
                    dt = os.path.getctime(os.path.join(root, name))
                except OSError:
                    continue
                dt = datetime.fromtimestamp(dt).strftime('%Y-%m-%d')
                dt = datetime.strptime(dt, '%Y-%m-%d')
                diff = (dtt - dt).days
            if name.lower().endswith(extensions) and diff <= days_int:
                if name.lower().endswith('.kfx') or name.lower().endswith('.azw8'):
                    is_kfx = True
                else:
                    is_kfx = False
                fide = name.decode('UTF-8')
                mobi_path = os.path.join(root, name)
                if is_kfx:
                    if '_sample' in fide:
                        continue
                    try:
                        kfx_metadata = get_kindle_kfx_metadata(mobi_path)
                    except Exception as e:
                        continue
                    doctype = kfx_metadata.get("cde_content_type")
                    if not doctype:
                        continue
                    asin = kfx_metadata.get("ASIN")
                else:
                    if '!DeviceUpgradeLetter!' in fide:
                        continue
                    with open(mobi_path, 'rb') as mf:
                        mobi_content = mf.read()
                        if mobi_content[60:68] != 'BOOKMOBI':
                            continue
                    section = kindle_unpack.Sectionizer(mobi_path)
                    mhlst = [kindle_unpack.MobiHeader(section, 0)]
                    mh = mhlst[0]
                    metadata = mh.getmetadata()
                    try:
                        asin = metadata['ASIN'][0]
                    except KeyError:
                        asin = None
                    try:
                        doctype = metadata['Document Type'][0]
                    except KeyError:
                        doctype = None
                if asin is None:
#########TU WSTAWIĆ FUNKCJĘ DODAJĄCA ASIN
                    continue
                thumbpath = os.path.join(
                    kindlepath, 'system', 'thumbnails',
                    'thumbnail_%s_%s_portrait.jpg' % (asin, doctype)
                )
                if (not os.path.isfile(thumbpath) or
                        (is_overwrite_pdoc_thumbs and doctype == 'PDOC') or
                        (is_overwrite_amzn_thumbs and (
                            doctype == 'EBOK' or doctype == 'EBSP'
                        ))):
                    if is_kfx:
                        image_data = kfx_metadata.get("cover_image_data")
                        if not image_data:
                            continue
                    try:
                        if is_kfx:
                            cover = image_data.decode('base64')
                        else:
                            cover = get_cover_image(section, mh, metadata,
                                                    doctype, name,
                                                    fide, is_verbose)
                    except IOError:
                        continue
                    if not cover:
                        continue
                    with open(thumbpath, 'wb') as f:
                        f.write(cover)
    if not skip_apnx:
        generate_apnx_files(docs, is_overwrite_apnx, days)

    return 0
