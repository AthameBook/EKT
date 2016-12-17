# -*- coding: utf-8 -*-
#
# Based on initial version Copyright © 2009 Charles M. Hannum root@ihack.net
# Extensions / Improvements Copyright © 2009-2012: P. Durrant, K.Hendricks,
# S. Siebert, fandrieu, DiapDealer, nickredding and bug fixes from many others.
# Stripped down for KindleButler Copyright (C) 2014 Pawel Jastrzebski
# <pawelj@vulturis.eu>
#

import struct

class Sectionizer:
    def __init__(self, filename):
        self.data = open(filename, 'rb').read()
        self.palmheader = self.data[:78]
        self.palmname = self.data[:32]
        self.ident = self.palmheader[0x3C:0x3C + 8]
        self.num_sections, = struct.unpack_from('>H', self.palmheader, 76)
        self.filelength = len(self.data)
        sectionsdata = struct.unpack_from('>%dL' % (self.num_sections * 2), self.data, 78) + (self.filelength, 0)  # noqa
        self.sectionoffsets = sectionsdata[::2]
        self.sectionattributes = sectionsdata[1::2]
        self.sectiondescriptions = ["" for x in range(self.num_sections + 1)]
        self.sectiondescriptions[-1] = "File Length Only"
        return

    def setsectiondescription(self, section, description):
        if section < len(self.sectiondescriptions):
            self.sectiondescriptions[section] = description

    def load_section(self, section):
        before, after = self.sectionoffsets[section:section + 2]
        return self.data[before:after]

class MobiHeader:
    id_map_hexstrings = {
        209: 'Tamper Proof Keys (hex)',
        300: 'Font Signature (hex)',
        403: 'Unknown_(403) (hex)',
        405: 'Unknown_(405) (hex)',
        407: 'Unknown_(407) (hex)',
        450: 'Unknown_(450) (hex)',
        451: 'Unknown_(451) (hex)',
        452: 'Unknown_(452) (hex)',
        453: 'Unknown_(453) (hex)',

    }

    id_map_strings = {
        1: 'Drm Server Id',
        2: 'Drm Commerce Id',
        3: 'Drm Ebookbase Book Id',
        100: 'Creator',
        101: 'Publisher',
        102: 'Imprint',
        103: 'Description',
        104: 'ISBN',
        105: 'Subject',
        106: 'Published',
        107: 'Review',
        108: 'Contributor',
        109: 'Rights',
        110: 'SubjectCode',
        111: 'Type',
        112: 'Source',
        113: 'ASIN',
        114: 'versionNumber',
        117: 'Adult',
        118: 'Price',
        119: 'Currency',
        122: 'fixed-layout',
        123: 'book-type',
        124: 'orientation-lock',
        126: 'original-resolution',
        127: 'zero-gutter',
        128: 'zero-margin',
        129: 'K8(129)_Masthead/Cover_Image',
        132: 'RegionMagnification',
        200: 'DictShortName',
        208: 'Watermark',
        501: 'Document Type',
        502: 'last_update_time',
        503: 'Updated_Title',
        504: 'ASIN_(504)',
        508: 'Title file-as',
        517: 'Creator file-as',
        522: 'Publisher file-as',
        524: 'Language_(524)',
        525: 'primary-writing-mode',
        527: 'page-progression-direction',
        528: 'Unknown_Logical_Value_(528)',
        529: 'Original_Source_Description_(529)',
        534: 'Unknown_(534)',
        535: 'Kindlegen_BuildRev_Number',

    }

    id_map_values = {
        115: 'sample',
        116: 'StartOffset',
        121: 'K8(121)_Boundary_Section',
        125: 'K8(125)_Count_of_Resources_Fonts_Images',
        131: 'K8(131)_Unidentified_Count',
        201: 'CoverOffset',
        202: 'ThumbOffset',
        203: 'Has Fake Cover',
        204: 'Creator Software',
        205: 'Creator Major Version',
        206: 'Creator Minor Version',
        207: 'Creator Build Number',
        401: 'Clipping Limit',
        402: 'Publisher Limit',
        404: 'Text to Speech Disabled',
        406: 'Rental_Indicator',
    }

    def __init__(self, sect, sectnumber):
        self.metadata = {}
        self.sect = sect
        self.start = sectnumber
        self.header = self.sect.load_section(self.start)
        if len(self.header) > 20 and self.header[16:20] == b'MOBI':
            self.sect.setsectiondescription(0, b"Mobipocket Header")
            self.palm = False
        elif self.sect.ident == b'TEXtREAd':
            self.sect.setsectiondescription(0, b"PalmDOC Header")
            self.palm = True

        self.records, = struct.unpack_from('>H', self.header, 0x8)

        self.title = self.sect.palmname
        self.length = len(self.header) - 16
        self.type = 3
        self.codepage = 1252
        self.codec = b'windows-1252'
        self.unique_id = 0
        self.version = 0
        self.hasexth = False
        self.exth = b''
        self.exth_offset = self.length + 16
        self.exth_length = 0
        self.crypto_type = 0
        self.firstnontext = self.start + self.records + 1
        self.firstresource = self.start + self.records + 1
        self.ncxidx = 0xffffffff
        self.metaorthindex = 0xffffffff
        self.metainflindex = 0xffffffff
        self.skelidx = 0xffffffff
        self.dividx = 0xffffffff
        self.othidx = 0xffffffff
        self.fdst = 0xffffffff
        self.mlstart = self.sect.load_section(self.start + 1)[:4]

        if self.palm:
            return

        self.length, self.type, self.codepage, self.unique_id, self.version = struct.unpack('>LLLLL', self.header[20:40])  # noqa
        codec_map = {
            1252: b'windows-1252',
            65001: b'utf-8',
        }
        if self.codepage in codec_map.keys():
            self.codec = codec_map[self.codepage]

        # title
        toff, tlen = struct.unpack('>II', self.header[0x54:0x5c])
        tend = toff + tlen
        self.title = self.header[toff:tend]

        exth_flag, = struct.unpack('>L', self.header[0x80:0x84])
        self.hasexth = exth_flag & 0x40
        self.exth_offset = self.length + 16
        self.exth_length = 0
        if self.hasexth:
            self.exth_length, = struct.unpack_from('>L', self.header, self.exth_offset + 4)  # noqa
            # round to next 4 byte boundary
            self.exth_length = ((self.exth_length + 3) >> 2) << 2
            self.exth = self.header[self.exth_offset:self.exth_offset + self.exth_length]  # noqa

        self.crypto_type, = struct.unpack_from('>H', self.header, 0xC)

        self.firstresource, = struct.unpack_from('>L', self.header, 0x6C)
        self.firstnontext, = struct.unpack_from('>L', self.header, 0x50)
        if self.firstresource != 0xffffffff:
            self.firstresource += self.start
        if self.firstnontext != 0xffffffff:
            self.firstnontext += self.start

        if self.version < 8:
            self.metaorthindex, = struct.unpack_from('>L', self.header, 0x28)
            if self.metaorthindex != 0xffffffff:
                self.metaorthindex += self.start

            self.metainflindex, = struct.unpack_from('>L', self.header, 0x2C)
            if self.metainflindex != 0xffffffff:
                self.metainflindex += self.start

        if self.length + 16 < 0xf8:
            return

        self.ncxidx, = struct.unpack('>L', self.header[0xf4:0xf8])
        if self.ncxidx != 0xffffffff:
            self.ncxidx += self.start

        if self.start != 0 or self.version == 8:
            self.skelidx, = struct.unpack_from('>L', self.header, 0xfc)
            if self.skelidx != 0xffffffff:
                self.skelidx += self.start

            self.dividx, = struct.unpack_from('>L', self.header, 0xf8)
            if self.dividx != 0xffffffff:
                self.dividx += self.start

            self.othidx, = struct.unpack_from('>L', self.header, 0x104)
            if self.othidx != 0xffffffff:
                self.othidx += self.start

            self.metaorthindex = 0xffffffff
            self.metainflindex = 0xffffffff

            self.fdst, = struct.unpack_from('>L', self.header, 0xc0)
            self.fdstcnt, = struct.unpack_from('>L', self.header, 0xc4)
            if self.fdstcnt <= 1:
                self.fdst = 0xffffffff
            if self.fdst != 0xffffffff:
                self.fdst += self.start

    def getmetadata(self):
        def addvalue(tmpname, tmpvalue):
            if tmpname not in self.metadata:
                self.metadata[tmpname] = [tmpvalue]
            else:
                self.metadata[tmpname].append(tmpvalue)
        if self.hasexth:
            extheader = self.exth
            _length, num_items = struct.unpack('>LL', extheader[4:12])
            extheader = extheader[12:]
            pos = 0
            for _ in range(num_items):
                tmpid, size = struct.unpack('>LL', extheader[pos:pos + 8])
                content = extheader[pos + 8: pos + size]
                if tmpid in MobiHeader.id_map_strings.keys():
                    name = MobiHeader.id_map_strings[tmpid]
                    addvalue(name, content)
                elif tmpid in MobiHeader.id_map_values.keys():
                    name = MobiHeader.id_map_values[tmpid]
                    if size == 9:
                        value, = struct.unpack('B', content)
                        addvalue(name, str(value))
                    elif size == 10:
                        value, = struct.unpack('>H', content)
                        addvalue(name, str(value))
                    elif size == 12:
                        value, = struct.unpack('>L', content)
                        addvalue(name, str(value))
                    else:
                        addvalue(name, content)
                elif tmpid in MobiHeader.id_map_hexstrings.keys():
                    name = MobiHeader.id_map_hexstrings[tmpid]
                    addvalue(name, content)
                else:
                    name = str(tmpid) + ' (hex)'
                    addvalue(name, content)
                pos += size
        return self.metadata
