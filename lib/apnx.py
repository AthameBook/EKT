# -*- coding: utf-8 -*-

__license__ = 'GPL v3'
__copyright__ = '2011, John Schember <john at nachtimwald.com>'
__docformat__ = 'restructuredtext en'

import struct
import os

import kindle_unpack
from lib.header import PdbHeaderReader

class APNXBuilder(object):

    def write_apnx(self, mobi_file_path, apnx_path, page_count=0):
        import uuid
        apnx_meta = {'guid': str(uuid.uuid4()).replace('-', '')[:8], 'asin':
                     '', 'cdetype': 'EBOK', 'format': 'MOBI_7', 'acr': ''}

        try:
            with open(mobi_file_path, 'rb') as mf:
                ident = PdbHeaderReader(mf).identity()
                if ident != 'BOOKMOBI':
                    return 1
                apnx_meta['acr'] = str(PdbHeaderReader(mf).name())
        except:
            return 1
        with open(mobi_file_path, 'rb') as mf:
            section = kindle_unpack.Sectionizer(mobi_file_path)
            mhlst = [kindle_unpack.MobiHeader(section, 0)]
            mh = mhlst[0]
            metadata = mh.getmetadata()
            if mh.version == 8:
                apnx_meta['format'] = 'MOBI_8'
            else:
                apnx_meta['format'] = 'MOBI_7'
            try:
                if metadata['Document Type'][0] is None:
                    apnx_meta['cdetype'] = 'EBOK'
                else:
                    apnx_meta['cdetype'] = 'EBOK'
                    apnx_meta['cdetype'] = metadata['Document Type'][0]
            except KeyError:
                apnx_meta['cdetype'] = 'EBOK'
            try:
                if metadata['ASIN'][0] is None:
                    apnx_meta['asin'] = ''
                else:
                    apnx_meta['asin'] = metadata['ASIN'][0]
            except KeyError:
                apnx_meta['asin'] = ''

        pages = []
        if page_count:
            pages = self.get_pages_exact(mobi_file_path, page_count)
        else:
            pages = self.get_pages_fast(mobi_file_path)

        if not pages:
            pages = self.get_pages_fast(mobi_file_path)
        if len(pages) > 65536:
            return

        apnx = self.generate_apnx(pages, apnx_meta)

        with open(apnx_path, 'wb') as apnxf:
            apnxf.write(apnx)

    def generate_apnx(self, pages, apnx_meta):
        apnx = ''

        if apnx_meta['format'] == 'MOBI_8':
            content_header = '{"contentGuid":"%(guid)s","asin":"%(asin)s","cdeType":"%(cdetype)s","format":"%(format)s","fileRevisionId":"1","acr":"%(acr)s"}' % apnx_meta
        else:
            content_header = '{"contentGuid":"%(guid)s","asin":"%(asin)s","cdeType":"%(cdetype)s","fileRevisionId":"1"}' % apnx_meta
        page_header = '{"asin":"%(asin)s","pageMap":"(1,a,1)"}' % apnx_meta

        apnx += struct.pack('>I', 65537)
        apnx += struct.pack('>I', 12 + len(content_header))
        apnx += struct.pack('>I', len(content_header))
        apnx += content_header
        apnx += struct.pack('>H', 1)
        apnx += struct.pack('>H', len(page_header))
        apnx += struct.pack('>H', len(pages))
        apnx += struct.pack('>H', 32)
        apnx += page_header

        for page in pages:
            apnx += struct.pack('>I', page)

        return apnx

    def get_pages_exact(self, mobi_file_path, page_count):
        pages = []
        count = 0

        with open(mobi_file_path, 'rb') as mf:
            phead = PdbHeaderReader(mf)
            r0 = phead.section_data(0)
            text_length = struct.unpack('>I', r0[4:8])[0]

        chars_per_page = int(text_length / page_count)
        while count < text_length:
            pages.append(count)
            count += chars_per_page

        if len(pages) > page_count:
            pages = pages[:page_count]

        return pages

    def get_pages_fast(self, mobi_file_path):
        text_length = 0
        pages = []
        count = 0

        with open(mobi_file_path, 'rb') as mf:
            phead = PdbHeaderReader(mf)
            r0 = phead.section_data(0)
            text_length = struct.unpack('>I', r0[4:8])[0]

        while count < text_length:
            pages.append(count)
            count += 2300

        return pages
