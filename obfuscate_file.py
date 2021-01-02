#!/usr/bin/env python3

"""
Obfuscate a macro-containing Word doc (optionally within a .zip file)
 using "File Buffer Collapsing", "Ghost File", or "Invalid Header" techniques

https://arielkoren.com/blog/2020/12/24/forging-malicious-doc/
"""

import sys
import os
import zipfile
from obfuscator import Obfuscator

def obfuscate_file(in_file, technique):
    """
    Obfuscate a given file with the specified technique

    The obfuscated output will be written to disk with its same filename.

    If the file to be obfuscated is a .docm, obfuscation will be performed on it directly.
    If it is a .zip containing .docm files, then a zip will be output containing all of the original files, with
    all of the .docm files obfuscated.

    """

    # If file is .docm, perform obfuscation directly
    if in_file[-5:] == '.docm':
        docm = Obfuscator(in_file)
        obfuscated = docm.get_obfuscated(technique)
        with open(in_file, 'wb') as f:
            f.write(bytearray(obfuscated))

    # If file is .zip, extract and perform obfuscation on each .docm
    else:
        z = zipfile.ZipFile(in_file, "r")
        filenames = z.namelist()
        for filename in filenames:
            z.extract(filename)
            if '.docm' in filename:
                ob_m = Obfuscator(filename)
                os.remove(filename)
                obfuscated = ob_m.get_obfuscated(technique)
                with open(filename, 'wb') as f:
                    f.write(bytearray(obfuscated))
        z.close()
        os.remove(in_file)
        zw = zipfile.ZipFile(in_file, "w")
        for filename in filenames:
            zw.write(filename)
        zw.close()
        for filename in filenames:
            if '.docm' not in filename:
                os.remove(filename)


def main(argv):
    usage = '''
    docmobfuscator.py <in_file> <obfuscation_technique>

    in_file must be .docm or .zip
    obfuscation_techniques: buffer_collapse, ghost_file, invalid_header, invalid_plus_buffer, invalid_plus_ghost

    make this usage nicer
    '''

    if len(argv) < 2 or len(argv) > 3:
        print(usage)
        sys.exit(2)
    if len(argv) == 2 and argv[1] == '-h':
        print(usage)
        sys.exit(2)

    in_file = argv[1]
    if in_file[-5:] != '.docm' and in_file[-4:] != '.zip':
        print('input must be .docm or .zip')
        sys.exit(2)

    if len(argv) > 2:
        technique = argv[2]
    else:
        technique = 'buffer_collapse'

    obfuscate_file(in_file, technique)


if __name__ == "__main__":
    main(sys.argv)
