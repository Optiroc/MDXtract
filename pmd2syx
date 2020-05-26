#!/usr/bin/env python3

# pmd2syx
#
# Utility to extract and convert instrument data embedded in PMD
# song files targeting the YM2608 and YM2151 sound chips. Common
# file extensions are .M and .M2. These files are the binary MML
# representation used by Professional Music Driver, a popular sound
# driver for many Japanese computers in the 1990s.
#
# The Yamaha "4-OP" instrument definitions are converted to DX7
# compatible sysex, usable on many popular software FM synthesizers
# as well as the original hardware.
#
# Usage:
# pmd2syx.py [-h, --help] [-v, --verbose] [infiles ...]
#
# - Instrument data will be converted and written as <filename>.syx
# - In verbose mode some intriguing data will be printed to stdout
#
# Project home:
#   https://github.com/Optiroc/MDXtract
#
# Yamaha "4-OP" to DX7 conversion tables and in-depth info:
#   https://sites.google.com/site/yalaorg/audio-music-synthesis/fmsynth/fmsynthdx
#
# Program by David Lindecrantz <optiroc@gmail.com>
# Distributed under the terms of the MIT license

import sys
import os
import argparse
import binascii
import common
import util

# -----------------------------------------------------------------------------
# PMD parser

# Make OPMOP from PMD voice definition
def PMDVoice_to_OPMOP(op, pmdv):
    return common.OPMOP(
        TL  = (pmdv[0x05 + op]) & 0xFF,
        AR  = (pmdv[0x09 + op]) & 0x1F,
        D1R = (pmdv[0x0D + op]) & 0x1F,
        D1L = (pmdv[0x15 + op] >> 4) & 0x0F,
        D2R = (pmdv[0x11 + op]) & 0x1F,
        RR  = (pmdv[0x15 + op]) & 0x0F,
        KS  = (pmdv[0x09 + op] >> 6) & 0x03,
        MUL = (pmdv[0x01 + op]) & 0x0F,
        DT1 = (pmdv[0x01 + op] >> 4) & 0x07,
        DT2 = (pmdv[0x11 + op] >> 6) & 0x03,
        AME = (pmdv[0x0D + op] >> 7) & 0x01
    )

# Make OPMVoice from PMD voice definition
def PMDVoice_to_OPMVoice(name, pmdv):
    return common.OPMVoice(
        name = name,
        FL   = (pmdv[0x19] >> 3) & 0x07,
        CON  = (pmdv[0x19]) & 0x07,
        SLOT = 0x0F,
        NE   = 0, NFRQ=0, AMS=0, PMS=0, LFRQ=63, WF=2, PMD=63, AMD=63,
        OPM1 = PMDVoice_to_OPMOP(0, pmdv),
        OPM2 = PMDVoice_to_OPMOP(1, pmdv),
        OPC1 = PMDVoice_to_OPMOP(2, pmdv),
        OPC2 = PMDVoice_to_OPMOP(3, pmdv)
    )

class PMD():
    def __init__(self, data):
        self.valid = False
        self.voice_data = []
        self.meta_data = {}

        # Assume not PMD file if not 0x1A at offset 1
        # TODO: Check valid values for offset 0
        if data[1] != 0x1A:
            return
        self.valid = True

        # Data offsets
        # 0-5 = FM MML data
        # 6-8 = PSG MML data
        # 9   = PCM MML data
        # 10  = Rhythm data
        # 11  = Metadata
        data_offsets = []
        for i in range(12):
            data_offsets.append(util.get_uint16(data, 2 + i * 2, True))

        # Voice data
        voice_len = 0x1A
        voice_offset = data_offsets[11] + 1
        while True:
            if voice_offset + voice_len > len(data):
                break
            self.voice_data.append(
                data[voice_offset: voice_offset + voice_len])
            voice_offset += voice_len
            if voice_offset >= len(data):
                break
            if data[voice_offset] == 0x00:
                break

        # Metadata
        meta_keys = ["ppz_file", "pps_file", "pcm_file", "title", "composer", "arranger", "memo1", "memo2"]
        for k in meta_keys:
            self.meta_data[k] = None

        meta_offset = voice_offset + 1
        if meta_offset + 1 >= len(data) or data[meta_offset] != 0xFF:
            return  # No metadata
        meta_bin = data[meta_offset + 1: len(data)].split(b'\0')

        for i, b in enumerate(meta_bin):
            try:
                if i >= len(meta_keys):
                    break
                dec = b.decode("shiftjis")
                if dec:
                    self.meta_data[meta_keys[i]] = dec
            except UnicodeDecodeError as _:
                continue


# -----------------------------------------------------------------------------
# Command Line Interface

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", dest="verbose", action="store_true", default=False, help="verbose output")
    parser.add_argument("infiles", nargs="*", help="input file(s)")

    try:
        arguments = parser.parse_args()
        if not arguments.infiles:
            parser.print_help()
            sys.exit(0)

        first = True
        for path in arguments.infiles:
            with open(path, "rb") as infile:
                basepath = os.path.abspath(os.path.join(
                    os.path.dirname(path), os.path.basename(path)))
                basename = os.path.splitext(os.path.basename(path))[0]

                # Parse PMD
                pmd = PMD(bytearray(infile.read()))

                if not pmd.valid or not pmd.voice_data:
                    if not first:
                        print()
                    first = False
                    print(
                        "File '{}' not recognized as PMD or contains no voice data".format(path))
                    continue

                if arguments.verbose:
                    if not first:
                        print()
                    first = False
                    print("File:    ", path)
                    print("Title:   ", pmd.meta_data["title"])
                    print("Composer:", pmd.meta_data["composer"])
                    print("Arranger:", pmd.meta_data["arranger"])
                    if pmd.meta_data["memo1"] is not None:
                        print("Notes:   ", pmd.meta_data["memo1"])
                        if pmd.meta_data["memo2"] is not None:
                            print("         ", pmd.meta_data["memo2"])
                    if pmd.meta_data["pcm_file"] is not None:
                        print("PCM File:", pmd.meta_data["pcm_file"])
                    if pmd.meta_data["ppz_file"] is not None:
                        print("PPZ File:", pmd.meta_data["ppz_file"])
                    if pmd.meta_data["pps_file"] is not None:
                        print("PPS File:", pmd.meta_data["pps_file"])
                    print("Voices:  ", len(pmd.voice_data))

                # Make OPMVoice list
                opmvoices = []
                for vd in pmd.voice_data:
                    voice_id = vd[0]
                    if arguments.verbose:
                        print("Voice {:02X}: {}".format(
                            voice_id, binascii.hexlify(vd).decode()))
                    vn = basename[:7] + "_{:02X}".format(voice_id)
                    opmvoices.append(PMDVoice_to_OPMVoice(vn, vd))

                # Make DX7Voice lists and render sysex (max 32 entries per batch allowed)
                batch_size = 32
                for i, opmv_batch in enumerate([opmvoices[c:c+batch_size] for c in range(0, len(opmvoices), batch_size)]):
                    outpath = "{}.syx".format(basepath)
                    if i > 0:
                        outpath = "{}_{}.syx".format(basepath, i)
                    dx7voices = []
                    for opmv in opmv_batch:
                        dx7voices.append(common.OPMVoice_to_DX7Voice(opmv))
                    with open(outpath, "wb") as f:
                        f.write(common.sysex_from_DX7Voices(dx7voices))

        return 0

    except IOError as err:
        print("{}".format(err))

if __name__ == "__main__":
    sys.exit(main())
