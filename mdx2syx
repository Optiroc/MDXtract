#!/usr/bin/env python3

# mdx2syx
#
# Utility to extract and convert instrument data from MDX files.
# MDX is a binary MML representation used by MXDRV, a popular
# sound driver for the Sharp X68000 computer. The YM2151 instrument
# definitions are converted to DX7 compatible sysex, usable on many
# popular software FM synthesizers as well as the original hardware.
#
# Usage:
# mdx2syx.py [-h, --help] [-v, --verbose] [infiles ...]
#
# - Instrument data will be converted and written as <filename>.syx
# - In verbose mode some intriguing data will be printed to stdout
#
# Project home:
#   https://github.com/Optiroc/MDXtract
#
# Further reading on MXDRV:
#   https://www16.atwiki.jp/mxdrv/pages/23.html
# Further reading on MDX:
#   http://vgmrips.net/wiki/MDX
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
# MDX parser

# Make OPMOP from MDX voice definition
def MDXVoice_to_OPMOP(op, mdxv):
    return common.OPMOP(
        TL  = (mdxv[0x07 + op]) & 0xFF,
        AR  = (mdxv[0x0B + op]) & 0x1F,
        D1R = (mdxv[0x0F + op]) & 0x1F,
        D1L = (mdxv[0x17 + op] >> 4) & 0x0F,
        D2R = (mdxv[0x13 + op]) & 0x1F,
        RR  = (mdxv[0x17 + op]) & 0x0F,
        KS  = (mdxv[0x0B + op] >> 6) & 0x03,
        MUL = (mdxv[0x03 + op]) & 0x0F,
        DT1 = (mdxv[0x03 + op] >> 4) & 0x07,
        DT2 = (mdxv[0x13 + op] >> 6) & 0x03,
        AME = (mdxv[0x0F + op] >> 7) & 0x01
    )

# Make OPMVoice from MDX voice definition
def MDXVoice_to_OPMVoice(name, mdxv):
    return common.OPMVoice(
        name = name,
        FL   = (mdxv[1] >> 3) & 0x07,
        CON  = (mdxv[1]) & 0x07,
        SLOT = (mdxv[2]) & 0xFF,
        NE   = 0, NFRQ=0, AMS=0, PMS=0, LFRQ=63, WF=2, PMD=63, AMD=63,
        OPM1 = MDXVoice_to_OPMOP(0, mdxv),
        OPM2 = MDXVoice_to_OPMOP(1, mdxv),
        OPC1 = MDXVoice_to_OPMOP(2, mdxv),
        OPC2 = MDXVoice_to_OPMOP(3, mdxv)
    )

class MDX():
    def __init__(self, data):
        self.title = None
        self.pdxfile = None
        self.voice_data = []

        # Assume MDX file if title terminator is found reasonably early
        title_end = data.find(bytearray([0x0d, 0x0a]))
        if title_end == -1 or title_end > 255:
            return

        # Get title string
        self.title = data[0:title_end].decode('shiftjis')

        # Get PDX file name
        pdx_start = title_end + 3
        data_start = pdx_start + 1
        if data[pdx_start] != 0:
            data_start = data.find(0x00, pdx_start) + 1
            self.pdxfile = data[pdx_start:data_start - 1].decode('shiftjis')

        # Get channel count
        # (16 bit words before first MML chunk, -1 for the voice offset)
        self.channels = (util.get_uint16(data, data_start + 2, True) >> 1) - 1

        # Get voice data
        voice_blob = data[util.get_uint16(data, data_start, True) + data_start: len(data)]
        voice_len = 0x1B
        voice_offset = 0
        while True:
            if voice_offset + voice_len <= len(voice_blob):
                self.voice_data.append(
                    voice_blob[voice_offset: voice_offset + voice_len])
                voice_offset += voice_len
            else:
                break

        # Get MML data
        #   Unused for the moment, but it might be cool to extract LFO settings
        #   applied to voices and incorporate in voice definitions.
        mml_offsets = []
        for i in range(self.channels):
            mml_offsets.append(util.get_uint16(data, data_start + 2 + (i * 2), True) + data_start)
        mml_offsets.append(util.get_uint16(data, data_start, True))

        self.mml_data = []
        for i in range(self.channels):
            self.mml_data.append(data[mml_offsets[i]: mml_offsets[i+1]])


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
            return 0

        first = True
        for path in arguments.infiles:
            with open(path, "rb") as infile:
                basepath = os.path.abspath(os.path.join(
                    os.path.dirname(path), os.path.basename(path)))
                basename = os.path.splitext(os.path.basename(path))[0]

                # Parse MDX
                mdx = MDX(bytearray(infile.read()))

                if mdx.title is None and not mdx.voice_data:
                    if first is False:
                        print()
                    first = False
                    print("File '{}' not recognized as MDX".format(path))
                    continue

                if arguments.verbose:
                    if first is False:
                        print()
                    first = False
                    print("File:", path)
                    print("Title:", mdx.title)
                    print("PCM File:", mdx.pdxfile)
                    print("Channels:", mdx.channels)
                    print("Voices:", len(mdx.voice_data))

                # Make OPMVoice list
                opmvoices = []
                for vd in mdx.voice_data:
                    voice_id = vd[0]
                    if arguments.verbose:
                        print("Voice {:02X}: {}".format(
                            voice_id, binascii.hexlify(vd).decode()))
                    vn = basename[:7] + "_{:02X}".format(voice_id)
                    opmvoices.append(MDXVoice_to_OPMVoice(vn, vd))

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
