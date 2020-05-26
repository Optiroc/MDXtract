#!/usr/bin/env python3

# pmd2wav
#
# Utility to extract data from the different sample archive
# formats used by the PMD music player and convert it to
# 16-bit WAV format PCM. The player was most commonly used
# in game software on the NEC PC-9801 series of computers,
# but saw some use on FM Towns, Sharp X1 and X68000 as well.
#
# Supported archive formats:
#  - PPC (YM2608 4-bit "DELTA-T" ADPCM)
#  - PVI (YM2608 4-bit "DELTA-T" ADPCM)
#  - P86 (PC-9801-86 8-bit "86PCM")
#  - P68 (OKI MSM6258V 4-bit ADPCM)
#  - PPS (SSG 4-bit PCM?)
#
# Usage:
# pmd2wav.py [-h] [-v] [--rate R] [--gain G] [--dcnorm] [infiles ...]
#
#   -h, --help        show help message
#   -v, --verbose     verbose output
#   --type [type]     archive type (ppc/pps/pvi/p86/p68, default: auto)
#   --rate R          output sample rate (default: 15625)
#   --gain G          output gain (default: 1.0)
#   --dcnorm          normalize dc bias
#
# - Auto type detection looks at the file header first, and if format
#   can't be deduced from that it falls back to the file extension.
# - Sample data will be converted and written as <filename>_<n>.wav
#
# All support formats except X68 and PPS include a file header,
# so combined with filename use a common header, so if no header
# is detected the tool tries to extract the archive as a "P"
# OKI ADPCM archive. This format is used in the X68000 version
# of Star Trader by Falcom.
#
# Note: Since the PMD player changed a lot over the years and
# supported many sample formats, I am certain this tool will surely
# fail with some files I haven't tested it with.
#
# Project home:
#   https://github.com/Optiroc/MDXtract
#
# Program by David Lindecrantz <optiroc@gmail.com>
# Distributed under the terms of the MIT license

import sys
import os
import struct
import audioop
import argparse
import common
import util

# -----------------------------------------------------------------------------
# Extract PCM from "PPC" archive

def extract_ppc(data):
    data_len = len(data)
    header_len = 30
    if data_len < header_len + 256 * 4 + 2:
        return bad_data()

    # Get offsets
    pcm_offsets = []
    for i in range(256):
        start = (util.get_uint16(data, 0x20 + i * 4) << 5)
        end = (util.get_uint16(data, 0x22 + i * 4) << 5) - 1
        pcm_offsets.append((start, end))

    # Get PCM data
    pcm_data = []

    pcm_ends = util.get_uint16(data, header_len) << 5
    pcm_ram = bytearray([0x00] * (0x26 << 5))
    pcm_ram.extend(data[0x420:])
    pcm_ram_len = len(pcm_ram)
    if pcm_ram_len != pcm_ends:
        return bad_data()

    for i, pcm_offset in enumerate(pcm_offsets):
        if (pcm_offset[1]) <= pcm_ram_len and pcm_offset[1] - pcm_offset[0] > 8:
            pcm = common.YM_ADPCM.decode(pcm_ram[pcm_offset[0]: pcm_offset[1]])
            pcm_data.append((pcm, "{:03}".format(i)))
        else:
            pcm_data.append(None)
    return "PPC", pcm_data


# -----------------------------------------------------------------------------
# Extract PCM from "PPS" archive

# Note: I found no documentation on this format, but it does seem like
#       4-bit PCM, presumably played through an SSG channel.

def extract_pps(data):
    data_len = len(data)
    header_len = 84
    if data_len < header_len:
        return bad_data()

    # Get offsets
    pcm_offsets = []
    for i in range(14):
        start = util.get_uint16(data, i * 6)
        end = start + util.get_uint16(data, i * 6 + 2) - 1
        if start > data_len:
            return bad_data()
        pcm_offsets.append((start, end))

    # Get PCM data
    pcm_data = []
    for i, pcm_offset in enumerate(pcm_offsets):
        if pcm_offset[0] > 0 and (pcm_offset[1]) <= data_len and pcm_offset[1] - pcm_offset[0] > 0x20:
            decoded = bytearray()
            for nibble in util.nibbles(data[pcm_offset[0]: pcm_offset[1] + 1], False):
                decoded.extend(struct.pack("b", util.clip_int8((nibble << 3) - 60)))
            pcm = bytearray(audioop.lin2lin(decoded, 1, 2))
            pcm_data.append((pcm, "{:03}".format(i)))
        else:
            pcm_data.append(None)
    return "PPS", pcm_data


# -----------------------------------------------------------------------------
# Extract PCM from "PVI" archive

def extract_pvi(data):
    data_len = len(data)
    if data_len < 0x210:
        return bad_data()

    # Get offsets
    pcm_offsets = []
    for i in range(128):
        start = end = 0
        if util.get_uint16(data, i * 4 + 0x12) != 0:
            start = (util.get_uint16(data, i * 4 + 0x10) << 5)
            end = (util.get_uint16(data, i * 4 + 0x12) << 5) - 1
        if end < start:
            end = start
        pcm_offsets.append((start + 0x210, end + 0x210))

    # Get PCM data
    pcm_data = []
    for i, pcm_offset in enumerate(pcm_offsets):
        if (pcm_offset[1]) <= data_len and pcm_offset[1] - pcm_offset[0] > 8:
            pcm = common.YM_ADPCM.decode(data[pcm_offset[0]: pcm_offset[1]])
            pcm_data.append((pcm, "{:03}".format(i)))
        else:
            pcm_data.append(None)
    return "PVI", pcm_data


# -----------------------------------------------------------------------------
# Extract PCM from "P86" archive

def extract_p86(data):
    data_len = len(data)
    header_len = 16
    if data_len < header_len + 256 * 6 + 2:
        return bad_data()
    if data_len != util.get_uint24(data, 0x0D):
        return bad_data()

    # Get offsets
    pcm_offsets = []
    for i in range(256):
        start = util.get_uint24(data, header_len + i * 6)
        if start > data_len:
            return bad_data()
        end = start + util.get_uint24(data, header_len + 3 + i * 6) - 1
        if end < 0:
            end = 0
        pcm_offsets.append((start, end))

    # Get PCM data
    pcm_data = []
    for i, pcm_offset in enumerate(pcm_offsets):
        if pcm_offset[0] > 0 and (pcm_offset[1]) <= data_len and pcm_offset[1] - pcm_offset[0] > 0x20:
            pcm = bytearray(audioop.lin2lin(
                data[pcm_offset[0]: pcm_offset[1] + 1], 1, 2))
            pcm_data.append((pcm, "{:03}".format(i)))
        else:
            pcm_data.append(None)
    return "P86", pcm_data


# -----------------------------------------------------------------------------
# Extract PCM from "P68" archive

def extract_p68(data):
    data_len = len(data)
    if data_len < 256 * 4 + 2:
        return bad_data()

    # Get offsets
    pcm_offsets = []
    for i in range(256):
        start = util.get_uint32(data, i * 4, True)
        if start > data_len:
            return bad_data()
        end = util.get_uint32(data, 4 + (i * 4), True) - 1
        if i > 0 and util.get_uint32(data, (i - 1) * 4, True) == data_len:
            pcm_offsets = pcm_offsets[0:-1]
            break
        pcm_offsets.append((start, end))

    # Get PCM data
    pcm_data = []
    for i, pcm_offset in enumerate(pcm_offsets):
        if pcm_offset[1] <= data_len and pcm_offset[1] - pcm_offset[0] > 8:
            pcm = common.OKI_ADPCM.decode(data[pcm_offset[0]: pcm_offset[1] + 1])
            pcm_data.append((pcm, "{:03}".format(i)))
        else:
            pcm_data.append(None)
    return "P68", pcm_data


# -----------------------------------------------------------------------------
# PMD PCM extraction

def extract_pcm(data, datatype=None, extension_type=None):
    if datatype is None:
        ppc_header = bytearray(b'ADPCM DATA for  PMD ver.4.4-  ')
        pvi_header = bytearray(b'PVI2')
        p86_header = bytearray(b'PCM86 DATA')

        if data[0: len(ppc_header)] == ppc_header:
            datatype = "PPC"
        elif data[0: len(pvi_header)] == pvi_header:
            datatype = "PVI"
        elif data[0: len(p86_header)] == p86_header:
            datatype = "P86"
        else:
            datatype = extension_type

    if datatype is "PPC":
        return extract_ppc(data)
    elif datatype is "PPS":
        return extract_pps(data)
    elif datatype is "PVI":
        return extract_pvi(data)
    elif datatype is "P86":
        return extract_p86(data)
    elif datatype is "P68":
        return extract_p68(data)
    else:
        return bad_data()


def bad_data():
    return False, []


# -----------------------------------------------------------------------------
# Command Line Interface

def str2type(s):
    s = s.replace('.', '').upper()
    if s in ["PPC"]:
        return "PPC"
    elif s in ["PPS"]:
        return "PPS"
    elif s in ["PVI"]:
        return "PVI"
    elif s in ["P86", "86PCM", "86"]:
        return "P86"
    elif s in ["P", "P68", "X86"]:
        return "P68"
    else:
        return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", dest="verbose", action="store_true", default=False, help="verbose output")
    parser.add_argument("--type", metavar="type", dest="type", type=str2type, nargs='?', const=None, default=None, help="archive type (ppc/pps/pvi/p86/p68, default: auto detect)")
    parser.add_argument("--rate", metavar="R", dest="sample_rate", type=int, default=15625, help="output sample rate (default: 15625)")
    parser.add_argument("--gain", metavar="G", dest="gain", type=float, default=1.0, help="output gain (default: 1.0)")
    parser.add_argument("--dcnorm", dest="dc_bias_norm", action="store_true", default=False, help="normalize dc bias")
    parser.add_argument("infiles", nargs="*", help="input file(s)")

    try:
        arguments = parser.parse_args()
        if not arguments.infiles:
            parser.print_help()
            return 0

        first = True
        for path in arguments.infiles:
            with open(path, "rb") as infile:
                ext_type = str2type(os.path.splitext(os.path.basename(path))[1])
                datatype, pcm_data = extract_pcm(bytearray(infile.read()), arguments.type, ext_type)

                if datatype is None or not pcm_data:
                    if not first:
                        print()
                    first = False
                    print("File '{}' not of recognized type or contains no sample data".format(path))
                    continue

                if arguments.verbose:
                    if not first:
                        print()
                    print("File:", path)
                    print("Type:", datatype)
                    first = False

                gain = arguments.gain
                if datatype == "P68":
                    gain *= 16.0

                basepath = os.path.abspath(os.path.join(
                    os.path.dirname(path), os.path.basename(path)))
                files_written = 0
                for pcm in pcm_data:
                    if pcm is not None:
                        outpath = "{}_{}.wav".format(basepath, pcm[1])
                        out_pcm = common.pcm_adjust(pcm[0], gain, arguments.dc_bias_norm)
                        common.wav_write(out_pcm, arguments.sample_rate, outpath)
                        if arguments.verbose:
                            print("- {} ({} samples)".format(os.path.basename(outpath), len(pcm[0]) // 2))
                        files_written += 1

                if arguments.verbose:
                    print("{} samples extracted".format(files_written))

        return 0

    except IOError as err:
        print("{}".format(err))

if __name__ == "__main__":
    sys.exit(main())
