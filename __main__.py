#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is based on ExtractCoverThumbs, licensed under
# GNU Affero GPLv3 or later.
# Copyright © Robert Błaut.

from lib.cleaner import Cleaner
from lib.extract_cover_thumbs import extract_cover_thumbs

kindlepath = '/mnt/us/'
days = '1000'

if __name__ == '__main__':
    Cleaner(kindlepath)
    extract_cover_thumbs(kindlepath, days)
