#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# GNU Affero GPLv3 or later.
# Copyright © Becky.

from lib.cleaner import Cleaner
from lib.extract_cover_thumbs import extract_cover_thumbs

kindlepath = '/mnt/us/'

if __name__ == '__main__':
    Cleaner(kindlepath)
    extract_cover_thumbs(kindlepath)
