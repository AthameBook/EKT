#!/usr/bin/python
# vim:fileencoding=UTF-8:ts=4:sw=4:sta:et:sts=4:ai

# python 2.7
from __future__ import (unicode_literals, division, absolute_import, print_function)
import collections
import datetime
import decimal
import json
import os
import StringIO
import struct

__license__   = 'GPL v3'
__copyright__ = '2016, John Howell <jhowell@acm.org>'

VERSION = '3.1'

CONTAINER_MAGIC = b'CONT'
ENTITY_MAGIC = b'ENTY'
ION_MAGIC = b'\xe0\x01\x00\xea'
DRMION_MAGIC = b'\xeaDRMION\xee'

DT_NULL = 0                 # None
DT_BOOLEAN = 1              # True/False
DT_POSITIVE_INTEGER = 2     # int
DT_NEGATIVE_INTEGER = 3     # int
DT_FLOAT = 4                # float
DT_DECIMAL = 5              # decimal.Decimal
DT_TIMESTAMP = 6            # datetime.datetime
DT_SYMBOL = 7               # unicode
DT_STRING = 8               # unicode
DT_CLOB = 9                 # unicode
DT_BLOB = 10                # str (byte string)
DT_LIST = 11                # list
DT_S_EXPRESSION = 12        # tuple
DT_STRUCT = 13              # OrderedDict of symbol/value pairs (order is sometimes important)
DT_TYPED_DATA = 14          # dict with 'type', 'id', 'value'

YJ_SYMBOLS = {
    7: "symbols",
    8: "max_id",
    10: "language",
    153: "title",
    154: "description",
    164: "external_resource",
    165: "location",
    169: "reading_orders",
    222: "author",
    224: "ASIN",
    232: "publisher",
    251: "cde_content_type",
    258: "metadata",
    307: "value",
    413: "bcIndexTabOffset",
    414: "bcIndexTabLength",
    415: "bcDocSymbolOffset",
    416: "bcDocSymbolLength",
    417: "bcRawMedia",
    424: "cover_image",
    490: "book_metadata",
    491: "categorised_metadata",
    492: "key",
    }

METADATA_ENTITY_TYPES = {164, 258, 417, 490}

def get_kindle_kfx_metadata(filepath):
    packed_data = read_file(filepath)

    if packed_data[0:8] == DRMION_MAGIC:
        altpath = os.path.join(os.path.splitext(filepath)[0] + ".sdr", "assets", "metadata.kfx")
        packed_data = read_file(altpath)
    return extract_metadata(KFXContainer(packed_data).decode(metadata_only=True))

def extract_metadata(container_data):
    metadata = {}

    def add_metadata(key, value):
        if key == "author":
            if "authors" not in metadata:
                metadata[key] = value
                metadata["authors"] = [value]
            elif value not in metadata["authors"]:
                metadata["authors"].append(value)
        else:
            metadata[key] = value

    for entity in container_data:
        if entity.type == "book_metadata":
            for category in entity.value["categorised_metadata"]:
                for meta in category["metadata"]:
                    add_metadata(meta["key"], meta["value"])

        if entity.type == "metadata":
            for key,value in entity.value.items():
                add_metadata(key, value)

    cover_image = metadata.get("cover_image")
    if cover_image:
        for entity in container_data:
            if entity.type == "external_resource" and entity.id == cover_image:
                location = entity.value["location"]
                break
        else:
            location = None
            
        if location:
            for entity in container_data:
                if entity.type == "bcRawMedia" and entity.id == location:
                    metadata["cover_image_data"] = entity.value
                    break

    return metadata

class PackedData:

    def __init__(self, data):
        self.buffer = data
        self.offset = 0

    def unpack_one(self, fmt, advance=True):
        return self.unpack_multi(fmt, advance)[0]

    def unpack_multi(self, fmt, advance=True):
        fmt = fmt.encode('ascii')
        result = struct.unpack_from(fmt, self.buffer, self.offset)
        if advance: self.advance(struct.calcsize(fmt))
        return result

    def extract(self, size):
        data = self.buffer[self.offset:self.offset + size]
        self.advance(size)
        return data

    def advance(self, size):
        self.offset += size

    def remaining(self):
        return len(self.buffer) - self.offset

class PackedBlock(PackedData):

    def __init__(self, data, magic):
        PackedData.__init__(self, data)

        self.magic = self.unpack_one('4s')

        self.version = self.unpack_one('<H')
        self.header_len = self.unpack_one('<L')

class KFXContainer(PackedBlock):

    def __init__(self, data):
        self.data = data
        PackedBlock.__init__(self, data, CONTAINER_MAGIC)

        container_info_offset = self.unpack_one("<L")
        container_info_length = self.unpack_one("<L")
        container_info = PackedIon(data[container_info_offset:container_info_offset + container_info_length]).decode()

        doc_symbol_length = container_info.get("bcDocSymbolLength")

        if doc_symbol_length:
            doc_symbol_offset = container_info["bcDocSymbolOffset"]
            self.symbol_data = data[doc_symbol_offset:doc_symbol_offset + doc_symbol_length]
        else:
            self.symbol_data = None
            
        self.entities = []
        index_table_length = container_info.get("bcIndexTabLength")

        if index_table_length:
            index_table_offset = container_info["bcIndexTabOffset"]
            entity_table = PackedData(data[index_table_offset:index_table_offset + index_table_length])

            while entity_table.remaining():
                entity_id, entity_type, entity_offset, entity_len = entity_table.unpack_multi('<LLQQ')
                entity_start = self.header_len + entity_offset
                self.entities.append(Entity(self.data[entity_start:entity_start + entity_len], entity_type, entity_id))

    def decode(self, metadata_only=False):
        symtab = dict(YJ_SYMBOLS)

        if self.symbol_data:
            ion_symbol_table = PackedIon(self.symbol_data).decode().value
            syms = ion_symbol_table["symbols"]
            min_id = ion_symbol_table["max_id"] - len(syms) + 1

            for i,sym in enumerate(syms):
                symtab[i + min_id] = sym

        return [entity.decode(symtab) for entity in self.entities if (not metadata_only) or (entity.entity_type in METADATA_ENTITY_TYPES)]

class TypedData(object):
    def __init__(self, type_, id, value):
        self.type = type_
        self.id = id
        self.value = value

class Entity(PackedBlock):

    def __init__(self, data, entity_type, entity_id, entity_data=None):
        self.entity_type = entity_type
        self.entity_id = entity_id

        if entity_data is not None:
            self.entity_data = entity_data
        else:
            PackedBlock.__init__(self, data, ENTITY_MAGIC)
            self.entity_data = data[self.header_len:]

    def decode(self, symtab):
        return TypedData(PackedIon(symtab=symtab).symbol_name(self.entity_type),
                    PackedIon(symtab=symtab).symbol_name(self.entity_id),
                    PackedIon(self.entity_data, symtab).decode() if PackedData(self.entity_data).unpack_one('4s') == ION_MAGIC
                            else self.entity_data.encode('base64'))

class KDFDatabase(object):

    def __init__(self, filename):
        import sqlite3      # version 3.8.2 or later required

        conn = sqlite3.connect(filename, 30)
        self.fragments = conn.execute('SELECT * FROM fragments;').fetchall()
        conn.close()

    def decode(self):
        fragments_data = []
        
        for id, payload_type, payload_value in self.fragments:
            if payload_type == "blob" and id != "max_id":
                fragment = PackedIon(StringIO.StringIO(payload_value).read()).decode()
                fragments_data.append(TypedData(fragment.id, id.encode('utf8'), fragment.value))

        return fragments_data

class PackedIon(PackedData):

    def __init__(self, data=b'', symtab=YJ_SYMBOLS):
        PackedData.__init__(self, data)
        self.symtab = symtab

    def decode(self):
        self.check_magic()
        return self.unpack_typed_value()

    def decode_list(self):
        self.check_magic()
        return self.unpack_list(self.remaining())

    def check_magic(self):
        self.magic = self.unpack_one('4s')

    def unpack_typed_value(self):
        cmd = self.unpack_one('B')

        data_type = cmd >> 4
        data_len = cmd & 0x0f
        if data_len == 14: data_len = self.unpack_unsigned_number()

        if data_type == DT_NULL:
            return None

        if data_type == DT_BOOLEAN:
            return data_len != 0  # length is actually value

        if data_type == DT_POSITIVE_INTEGER:
            return self.unpack_unsigned_int(data_len)

        if data_type == DT_NEGATIVE_INTEGER:
            return -self.unpack_unsigned_int(data_len)

        if data_type == DT_FLOAT:
            if data_len == 0: return float(0.0)
            return struct.unpack_from(b'>d', self.extract(data_len))[0]     # length must be 8

        if data_type == DT_DECIMAL:
            if data_len == 0: return decimal.Decimal(0)
            ion = PackedIon(self.extract(data_len), self.symtab)
            scale = ion.unpack_signed_number()
            magnitude = ion.unpack_signed_int(ion.remaining())
            return decimal.Decimal(magnitude) * (decimal.Decimal(10) ** scale)

        if data_type == DT_TIMESTAMP:
            ion = PackedIon(self.extract(data_len), self.symtab)
            ion.unpack_unsigned_number()        # unknown
            year = ion.unpack_unsigned_number()
            month = ion.unpack_unsigned_number()
            day = ion.unpack_unsigned_number()
            hour = ion.unpack_unsigned_number()
            minute = ion.unpack_unsigned_number()
            second = ion.unpack_unsigned_number()
            ion.unpack_unsigned_number()        # unknown
            return datetime.datetime(year, month, day, hour, minute, second)

        if data_type == DT_SYMBOL:
            return self.symbol_name(self.unpack_unsigned_int(data_len))

        if data_type == DT_STRING:
            return self.extract(data_len).decode('utf8')

        if data_type == DT_CLOB:
            return self.extract(data_len).decode('utf8')

        if data_type == DT_BLOB:
            return self.extract(data_len).encode('base64')

        if data_type == DT_LIST:
            return self.unpack_list(data_len)

        if data_type == DT_S_EXPRESSION:
            return tuple(self.unpack_list(data_len))

        if data_type == DT_STRUCT:
            ion = PackedIon(self.extract(data_len), self.symtab)
            result = collections.OrderedDict()

            while (ion.remaining()):
                symbol = self.symbol_name(ion.unpack_unsigned_number())
                result[symbol] = ion.unpack_typed_value()

            return result

        if data_type == DT_TYPED_DATA:
            ion = PackedIon(self.extract(data_len), self.symtab)
            type_ = self.symbol_name(ion.unpack_unsigned_number())
            id = self.symbol_name(ion.unpack_unsigned_number())
            value = ion.unpack_typed_value()
            return TypedData(type_, id, value)

        self.advance(data_len)
        return None

    def unpack_list(self, length):
        ion = PackedIon(self.extract(length), self.symtab)
        result = []

        while (ion.remaining()):
            result.append(ion.unpack_typed_value())

        return result

    def unpack_unsigned_number(self):
        number = 0
        while (True):
            byte = self.unpack_one('B')
            number = (number << 7) | (byte & 0x7f)
            if byte >= 0x80:
                return number

    def unpack_signed_number(self):
        value = self.unpack_one('B')
        if (value & 0x80) == 0: raise Exception('encountered multi-byte signed number')
        if (value & 0x40): return -(value & 0x3f)
        return (value & 0x7f)

    def unpack_unsigned_int(self, length):
        return struct.unpack_from(b'>Q', chr(0)*(8-length) + self.extract(length))[0]

    def unpack_signed_int(self, length):
        if length == 0: return 0

        first_byte = self.unpack_one('B', advance=False)
        if (first_byte & 0x80) != 0:
            self.advance(1)
            return -struct.unpack_from(b'>Q', chr(0)*(7-length) + chr(first_byte & 0x7f) + self.extract(length-1))[0]

        return self.unpack_unsigned_int(length)

    def symbol_name(self, symbol_number):
        return self.symtab.get(symbol_number, "S%d" % symbol_number)

def hexs(string, sep=' '):
    return sep.join('%02x' % ord(b) for b in string)

class IonEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            return float(o)

        if type(o).__name__ == "datetime":
            return o.isoformat()

        if type(o).__name__ == "TypedData":
            return {"type": o.type, "id": o.id, "value": o.value}

        return super(IonEncoder, self).default(o)

def json_dump(data, sort_keys=False):
    return json.dumps(data, indent=2, separators=(',', ': '), cls=IonEncoder, sort_keys=sort_keys)

def read_file(filename):
    with open(filename, 'rb') as of:
        return of.read()

def write_file(filename, data):
    with open(filename, 'wb') as of:
        of.write(data)
