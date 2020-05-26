#!/usr/bin/env python3

# pdx2wav
#
# Utility to extract and convert sample data from PDX file.
# PDX is the sample archive format used by MXDRV, a popular
# sound driver for the Sharp X68000 computer. The 4 bits per
# sample ADPCM data is converted to 16 bit uncompressed PCM.
#
# Usage:
# pdx2wav.py [-h] [-v] [--rate R] [--gain G] [--dcnorm] [infiles ...]
#
#   -h, --help        show help message
#   -v, --verbose     verbose output
#   --rate R          output sample rate (default: 15625)
#   --gain G          output gain (default: 1.0)
#   --dcnorm          normalize dc bias
#
# - ADPCM data will be converted and written as <filename>_<n>.wav
#
# Project home:
#   https://github.com/Optiroc/MDXtract
#
# Further reading on MXDRV:
#   https://www16.atwiki.jp/mxdrv/pages/23.html
#
# Program by David Lindecrantz <optiroc@gmail.com>
# Distributed under the terms of the MIT license

import sys
import os
import argparse
import common
import util

# -----------------------------------------------------------------------------
# PDX parser

class PDX():
    def __init__(self, data):
        # Get PCM offsets,lengths
        pcm_offsets = []
        filesize = len(data)
        for i in range(96):
            pcm_offset = (util.get_uint32(data, i * 8, True),
                          util.get_uint32(data, 4 + (i * 8), True))
            pcm_offsets.append(pcm_offset)

        # Get PCM data
        self.pcm_data = []
        for i, pcm_offset in enumerate(pcm_offsets):
            if pcm_offset[1] > 1 and (pcm_offset[0] + pcm_offset[1]) <= filesize:
                pcm = common.OKI_ADPCM.decode(
                    data[pcm_offset[0]: pcm_offset[0] + pcm_offset[1]])
                self.pcm_data.append((pcm, "{:03}".format(i)))
            else:
                self.pcm_data.append(None)


# -----------------------------------------------------------------------------
# Command Line Interface

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", dest="verbose", action="store_true", default=False, help="verbose output")
    parser.add_argument("--rate", metavar="R", dest="sample_rate", type=int, default=15625, help="wav file sample rate (default: 15625)")
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
                if arguments.verbose:
                    if first is False:
                        print()
                    print("File:", path)
                    first = False

                gain = arguments.gain * 16.0

                basepath = os.path.abspath(os.path.join(os.path.dirname(path), os.path.basename(path)))
                pdx = PDX(bytearray(infile.read()))

                files_written = 0
                for pcm in pdx.pcm_data:
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
