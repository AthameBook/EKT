#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Based on ExtractCoverThumbs
# Copyright © Robert Błaut.
# Current version: © Becky
# GNU Affero GPLv3 or later.

from __future__ import unicode_literals
import os
import sqlite3
from imghdr import what
from io import BytesIO
import kindle_unpack
from lib.apnx import APNXBuilder
from lib.pages import find_exth
from lib.pages import get_pages
from lib.kfxmeta import get_kindle_kfx_metadata
from lib.dualmetafix import DualMobiMetaFix
from PIL import Image

tablica = 'DeviceContentEntry'
polozenie = 'p_location'
miniatura = 'p_thumbnail'
baza = '/var/local/dcm.db'

def get_cover_image(section, mh, metadata, file, fide):
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
        if tmptype in [b"FLIS", b"FCIS", b"FDST", b"DATP", b"SRCS", b"CMET", b"FONT", b"RESC", b"GIF8"]:
            imgnames.append(None)
            continue
        if data == chr(0xe9) + chr(0x8e) + "\r\n".encode('UTF-8'):
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
           return process_image(data)
    return False

def process_image(data):
    cover = Image.open(BytesIO(data))
    cover.thumbnail((305, 470), Image.ANTIALIAS)
    if cover.size[0] < 280:
        wpercent = (305 / float(cover.size[0]))
        hsize = int((float(cover.size[1]) * float(wpercent)))
        cover = cover.resize((305, hsize), Image.ANTIALIAS)
    cover = cover.convert('L')
    return cover

def extract_cover_thumbs(kindlepath):
    docs = os.path.join(kindlepath, 'documents')
    extensions = ('.azw', '.azw3', '.mobi', '.pobi', '.kfx', '.azw8')
    
    conn = sqlite3.connect(baza)
    c = conn.cursor()
    c.execute('SELECT {cn}, {coi} FROM {tn} WHERE {coi} IS NOT NULL AND {coi} != "0"'.\
        format(coi=miniatura, tn=tablica, cn=polozenie))
    files = c.fetchall()
    conn.close()

    for names in files:
        name = names[0]
        nameonly = os.path.basename(name)
        thumbpath = names[1]
        if os.path.isfile(name.encode('UTF-8')):
            if name.lower().endswith(extensions):
                if name.lower().endswith('.kfx') or name.lower().endswith('.azw8'):
                    is_kfx = True
                else:
                    is_kfx = False
                if (not os.path.isfile(thumbpath)):
                    fide = name.encode('UTF-8')
                    if is_kfx:
                        if '_sample' in fide:
                            continue
                        try:
                            kfx_metadata = get_kindle_kfx_metadata(name)
                        except Exception as e:
                            continue
                    else:
                        with open(name.encode('UTF-8'), 'rb') as mf:
                            mobi_content = mf.read()
                            if mobi_content[60:68] != 'BOOKMOBI':
                                continue
                        section = kindle_unpack.Sectionizer(name.encode('UTF-8'))
                        mhlst = [kindle_unpack.MobiHeader(section, 0)]
                        mh = mhlst[0]
                        metadata = mh.getmetadata()
                    if is_kfx:
                        image_data = kfx_metadata.get("cover_image_data")
                        if not image_data:
                            continue
                    try:
                        if is_kfx:
                            cover = process_image(image_data.decode('base64'))
                        else:
                            cover = get_cover_image(section, mh, metadata, name, nameonly)
                    except IOError:
                        continue
                    if not cover:
                        continue
                    cover.save(thumbpath)
            
            apnx_builder = APNXBuilder()
            if name.lower().endswith(('.azw3', '.mobi', '.azw')):
                sdr_dir = os.path.join(os.path.splitext(name)[0] + '.sdr')
                if not os.path.isdir(sdr_dir.encode('UTF-8')):
                    os.makedirs(sdr_dir)
                apnx_path = os.path.join(sdr_dir, os.path.splitext(nameonly)[0] + '.apnx')
                if not os.path.isfile(apnx_path.encode('UTF-8')):
                    apnx_builder.write_apnx(name, apnx_path)

    return 0
