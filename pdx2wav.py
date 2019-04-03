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
import struct
import math
import argparse

#-----------------------------------------------------------------------------
# Utility functions

def clip_int(value, min_value, max_value):
  return int(max(min_value, min(value, max_value)))

def clip_int16(value):
  return int(max(-32768, min(value, 32767)))

def get_uint16(data, offset, big_endian=False):
  if not big_endian:
    return data[offset] + (data[offset + 1] << 8)
  else:
    return (data[offset] << 8) + data[offset + 1]

def get_uint24(data, offset, big_endian=False):
  if not big_endian:
    return (data[offset + 2] << 16) + (data[offset + 1] << 8) + data[offset + 0]
  else:
    return (data[offset + 0] << 16) + (data[offset + 1] << 8) + data[offset + 2]

def get_uint32(data, offset, big_endian=False):
  if not big_endian:
    return (data[offset + 3] << 24) + (data[offset + 2] << 16) + (data[offset + 1] << 8) + data[offset + 0]
  else:
    return (data[offset + 0] << 24) + (data[offset + 1] << 16) + (data[offset + 2] << 8) + data[offset + 3]

def nibbles(data, big_endian=False):
  shift = [0,4] if not big_endian else [4,0]
  for byte in data:
    for s in shift:
      yield (byte >> s) & 0x0F


#-----------------------------------------------------------------------------
# OKI MSM6258V ADPCM decoder

class OKI_ADPCM():
  def make_diff_lut():
    bitmap = [
        [ 1, 0, 0, 0], [ 1, 0, 0, 1], [ 1, 0, 1, 0], [ 1, 0, 1, 1],
        [ 1, 1, 0, 0], [ 1, 1, 0, 1], [ 1, 1, 1, 0], [ 1, 1, 1, 1],
        [-1, 0, 0, 0], [-1, 0, 0, 1], [-1, 0, 1, 0], [-1, 0, 1, 1],
        [-1, 1, 0, 0], [-1, 1, 0, 1], [-1, 1, 1, 0], [-1, 1, 1, 1]
    ]
    diff_lut = [0] * (49 * 16)
    for step in range(49):
      stepval = int(math.floor(16.0 * pow(11.0 / 10.0, float(step))))
      for n in range(16):
        diff_lut[step * 16 + n] = bitmap[n][0] * (stepval * bitmap[n][1] + stepval // 2 * bitmap[n][2] + stepval // 4 * bitmap[n][3] + stepval // 8)
    return diff_lut

  diff_lut = make_diff_lut()
  step_lut = [-1, -1, -1, -1, 2, 4, 6, 8, -1, -1, -1, -1, 2, 4, 6, 8]
  step_max = 48
  step_min = 0

  def decode(data):
    decoded = bytearray()
    signal = -2
    step = 0
    for nibble in nibbles(data, False):
      signal += OKI_ADPCM.diff_lut[step * 16 + nibble]
      signal = clip_int16(signal)
      step += OKI_ADPCM.step_lut[nibble]
      step = clip_int(step, OKI_ADPCM.step_min, OKI_ADPCM.step_max)
      decoded.extend(struct.pack("<h", signal))
    return decoded


#-----------------------------------------------------------------------------
# WAV writer

def wav_write(data, sample_rate, path):
  bits_per_sample = 16
  header = bytearray()
  # ChunkID
  header.extend(b"RIFF")
  # ChunkSize
  header.extend(struct.pack("<L", 36 + len(data)))
  # Format
  header.extend(b"WAVE")
  # Subchunk1ID
  header.extend(b"fmt ")
  # Subchunk1Size
  header.extend(struct.pack("<L", 16))
  # AudioFormat
  header.extend(struct.pack("<H", 1))
  # NumChannels
  header.extend(struct.pack("<H", 1))
  # SampleRate
  header.extend(struct.pack("<L", sample_rate))
  # ByteRate
  header.extend(struct.pack("<L", sample_rate * (bits_per_sample // 8)))
  # BlockAlign
  header.extend(struct.pack("<H", bits_per_sample // 8))
  # BitsPerSample
  header.extend(struct.pack("<H", bits_per_sample))
  # Subchunk2ID
  header.extend(b"data")
  # Subchunk2Size
  header.extend(struct.pack("<L", len(data)))
  # Write
  with open(path, "wb") as f:
    f.write(header)
    f.write(data)


#-----------------------------------------------------------------------------
# Add gain and adjust DC offset

def pcm_adjust(pcm, gain = 1, fix_dc_offset = True):
  if len(pcm) % 2: return pcm

  dc_bias = 0
  if fix_dc_offset is True:
    summ = 0
    for i in range(len(pcm) // 2):
      summ += struct.unpack("<h", pcm[i * 2 : i * 2 + 2])[0]
    dc_bias = summ // (len(pcm) // 2)

  adjusted = bytearray()
  for i in range(len(pcm) // 2):
    val = struct.unpack("<h", pcm[i * 2 : i * 2 + 2])[0]
    adjusted.extend(struct.pack("<h", clip_int16((val - dc_bias) * gain)))
  return adjusted


#-----------------------------------------------------------------------------
# PDX parser

class PDX():
  def __init__(self, data):
    # Get PCM offsets,lengths
    pcm_offsets = []
    filesize = len(data)
    for i in range(96):
      pcm_offset = (get_uint32(data, i * 8, True), get_uint32(data, 4 + (i * 8), True))
      pcm_offsets.append(pcm_offset)

    # Get PCM data
    self.pcm_data = []
    for i,pcm_offset in enumerate(pcm_offsets):
      if pcm_offset[1] > 1 and (pcm_offset[0] + pcm_offset[1]) <= filesize:
        pcm = OKI_ADPCM.decode(data[pcm_offset[0] : pcm_offset[0] + pcm_offset[1]])
        self.pcm_data.append((pcm, "{:03}".format(i)))
      else:
        self.pcm_data.append(None)


#-----------------------------------------------------------------------------
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
          if first is False: print()
          print("File:", path)
          first = False

        gain = arguments.gain * 16.0

        basepath = os.path.abspath(os.path.join(os.path.dirname(path), os.path.basename(path)))
        pdx = PDX(bytearray(infile.read()))

        files_written = 0
        for pcm in pdx.pcm_data:
          if pcm is not None:
            outpath = "{}_{}.wav".format(basepath, pcm[1])
            out_pcm = pcm_adjust(pcm[0], gain, arguments.dc_bias_norm)
            wav_write(out_pcm, arguments.sample_rate, outpath)
            if arguments.verbose: print("- {} ({} samples)".format(os.path.basename(outpath), len(pcm[0]) // 2))
            files_written += 1

        if arguments.verbose:
          print("{} samples extracted".format(files_written))

    return 0

  except IOError as err:
    print("{}".format(err))

if __name__ == "__main__":
  sys.exit(main())
