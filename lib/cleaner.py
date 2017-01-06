#!/usr/bin/python
# -*- coding:utf-8 -*-

import glob, os, shutil
import sqlite3

def Cleaner(kindlepath) :

    tablica = 'DeviceContentEntry'
    polozenie = 'p_location'
    miniatura = 'p_thumbnail'
    baza = '/var/local/dcm.db'

    documentsPath = kindlepath + 'documents'
    miniaturkipath = os.path.join(kindlepath, 'system', 'thumbnails')
    mrchpath = os.path.join(kindlepath, 'system', '.mrch')
    
    list_dirs = os.walk(documentsPath)
    root_dirs = os.listdir(kindlepath)

    problem = 0
    clean = False

    for files in root_dirs:
        if ( files[:18] == 'wininfo_screenshot' and files.endswith('.txt')):
            os.chdir(kindlepath)
            os.remove(files)

    for root, dirs, files in os.walk(kindlepath):
        for name in files:
            if name.lower().endswith('.partial'):
                partial = os.path.join(root, name)
                os.remove(partial)

    conn = sqlite3.connect(baza)
    conn.row_factory = lambda cursor, row: row[0]
    c = conn.cursor()
    c.execute('SELECT {coi} FROM {tn} WHERE {coi} IS NOT NULL AND {coi} != "0"'.\
        format(coi=miniatura, tn=tablica, cn=polozenie))
    PlikiMiniaturek = c.fetchall()
    conn.close()

    for root, dirs, files in os.walk(miniaturkipath):
        del dirs[:]
        for name in files:
            if name.lower().endswith('.jpg'):
                name = os.path.join(miniaturkipath,  name)

                if name in PlikiMiniaturek:
                    continue
                else:
                    os.remove(name)

    for files in os.listdir(documentsPath):
        if files.endswith('_ASC'):
            os.chdir(documentsPath)
            os.remove(files)

    for root, dirs, files in list_dirs:
        for numb in dirs:
            if numb:
                os.chdir(root)

                sdr = glob.glob(r'*.sdr')
                azw = glob.glob(r'*.azw')
                azw3 = glob.glob(r'*.azw3')
                pdf = glob.glob(r'*.pdf')
                txt = glob.glob(r'*.txt')
                prc = glob.glob(r'*.prc')
                mobi = glob.glob(r'*.mobi')
                pobi = glob.glob(r'*.pobi')
                azw4 = glob.glob(r'*.azw4')
                kfx = glob.glob(r'*.kfx')

                format_sdr = False

                for unsdr in sdr:
                    if unsdr[-4:] == '.sdr':
                        format_sdr = True
                        break

                if format_sdr == True:

                    for unsdr in sdr:
                        sdr_self = os.path.dirname(os.path.abspath('__file__'))

                        if unsdr[-4:] == sdr_self[-4:]:
                            continue

                        found = False
                        for n1 in azw:
                            if unsdr[:-4] == n1[:-4]:
                                found = True
                                break
                        for n2 in azw3:
                            if unsdr[:-4] == n2[:-5]:
                                found = True
                                break
                        for n3 in pdf:
                            if unsdr[:-4] == n3[:-4]:
                                found = True
                                break
                        for n4 in txt:
                            if unsdr[:-4] == n4[:-4]:
                                found = True
                                break
                        for n5 in prc:
                            if unsdr[:-4] == n5[:-4]:
                                found = True
                                break
                        for n6 in mobi:
                            if unsdr[:-4] == n6[:-5]:
                                found = True
                                break
                        for n7 in pobi:
                            if unsdr[:-4] == n7[:-5]:
                                found = True
                                break
                        for n8 in kfx:
                            if unsdr[:-4] == n8[:-4]:
                                found = True
                                break
                        for n9 in azw4:
                            if unsdr[:-4] == n9[:-5]:
                                found = True
                                break

                        if found == False:
                            try:
                                shutil.rmtree(unsdr)
                            except OSError, (errno, strerror):
                                problem = 1
                            clean = True
                break

        for name in dirs:
            if os.path.isdir(name):
                if len(os.listdir(name)) == 0:
                    empty = os.path.join(root, name)
                    os.rmdir(empty)

    if os.path.isdir(mrchpath):
        shutil.rmtree(mrchpath)
        open(mrchpath, 'w').close()
