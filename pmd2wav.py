#!/usr/local/bin/python3

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
import math
import audioop
import argparse

#-----------------------------------------------------------------------------
# Utility functions

def clip_int(value, min_value, max_value):
  return int(max(min_value, min(value, max_value)))

def clip_int16(value):
  return int(max(-32768, min(value, 32767)))

def clip_int8(value):
  return int(max(-128, min(value, 127)))

def get_uint16(bytes, offset, big_endian=False):
  if not big_endian:
    return bytes[offset] + (bytes[offset + 1] << 8)
  else:
    return (bytes[offset] << 8) + bytes[offset + 1]

def get_uint24(bytes, offset, big_endian=False):
  if not big_endian:
    return (bytes[offset + 2] << 16) + (bytes[offset + 1] << 8) + bytes[offset + 0]
  else:
    return (bytes[offset + 0] << 16) + (bytes[offset + 1] << 8) + bytes[offset + 2]

def get_uint32(bytes, offset, big_endian=False):
  if not big_endian:
    return (bytes[offset + 3] << 24) + (bytes[offset + 2] << 16) + (bytes[offset + 1] << 8) + bytes[offset + 0]
  else:
    return (bytes[offset + 0] << 24) + (bytes[offset + 1] << 16) + (bytes[offset + 2] << 8) + bytes[offset + 3]

def nibbles(bytes, big_endian=False):
  shift = [0,4] if not big_endian else [4,0]
  for byte in bytes:
    for s in shift:
      yield (byte >> s) & 0x0F


#-----------------------------------------------------------------------------
# Yamaha "DELTA-T" ADPCM decoder

class YM_ADPCM(object):
  diff_lut = [ 1,  3,  5,  7,  9, 11, 13, 15,  -1, -3, -5, -7, -9,-11,-13,-15]
  step_lut = [57, 57, 57, 57, 77,102,128,153,  57, 57, 57, 57, 77,102,128,153]
  step_max = 24576
  step_min = 127

  def decode(data):
    decoded = bytearray()
    signal =  0
    step = 127
    for nibble in nibbles(data, True):
      signal += (step * YM_ADPCM.diff_lut[nibble]) / 8
      signal = clip_int16(signal)
      step = (step * YM_ADPCM.step_lut[nibble]) / 64
      step = clip_int(step, YM_ADPCM.step_min, YM_ADPCM.step_max)
      decoded.extend(struct.pack("<h", signal))
    return decoded


#-----------------------------------------------------------------------------
# OKI MSM6258V ADPCM decoder

class OKI_ADPCM(object):
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
      for nyb in range(16):
        diff_lut[step * 16 + nyb] = bitmap[nyb][0] * (stepval * bitmap[nyb][1] + stepval // 2 * bitmap[nyb][2] + stepval // 4 * bitmap[nyb][3] + stepval // 8)
    return diff_lut

  step_lut = [-1, -1, -1, -1, 2, 4, 6, 8, -1, -1, -1, -1, 2, 4, 6, 8]
  step_max = 48
  step_min = 0
  diff_lut = make_diff_lut()

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
    sum = 0
    for i in range(len(pcm) // 2):
      sum += struct.unpack("<h", pcm[i * 2 : i * 2 + 2])[0]
    dc_bias = sum // (len(pcm) // 2)

  adjusted = bytearray()
  for i in range(len(pcm) // 2):
    val = struct.unpack("<h", pcm[i * 2 : i * 2 + 2])[0]
    adjusted.extend(struct.pack("<h", clip_int16((val - dc_bias) * gain)))
  return adjusted


#-----------------------------------------------------------------------------
# Extract PCM from "PPC" archive

def extract_ppc(data):
  data_len = len(data)
  header_len = 30
  if data_len < header_len + 256 * 4 + 2: return bad_data()

  # Get offsets
  pcm_offsets = []
  for i in range(256):
    start = (get_uint16(data, 0x20 + i * 4) << 5)
    end = (get_uint16(data, 0x22 + i * 4) << 5) - 1
    pcm_offsets.append((start, end))

  # Get PCM data
  pcm_data = []

  pcm_ends = get_uint16(data, header_len) << 5
  pcm_ram = bytearray([0x00] * (0x26 << 5))
  pcm_ram.extend(data[0x420:])
  pcm_ram_len = len(pcm_ram)
  if pcm_ram_len != pcm_ends: return bad_data()

  for i,pcm_offset in enumerate(pcm_offsets):
    if (pcm_offset[1]) <= pcm_ram_len and pcm_offset[1] - pcm_offset[0] > 8:
      pcm = YM_ADPCM.decode(pcm_ram[pcm_offset[0] : pcm_offset[1]])
      pcm_data.append((pcm, "{:03}".format(i)))
    else:
      pcm_data.append(None)
  return "PPC",pcm_data


#-----------------------------------------------------------------------------
# Extract PCM from "PPS" archive

# Note: I found no documentation on this format, but it does seem like
#       4-bit PCM, presumably played through an SSG channel.

def extract_pps(data):
  data_len = len(data)
  header_len = 84
  if data_len < header_len: return bad_data()

  # Get offsets
  pcm_offsets = []
  for i in range(14):
    start = get_uint16(data, i * 6)
    end = start + get_uint16(data, i * 6 + 2) - 1
    if start > data_len: return bad_data()
    pcm_offsets.append((start, end))

  # Get PCM data
  pcm_data = []
  for i,pcm_offset in enumerate(pcm_offsets):
    if pcm_offset[0] > 0 and (pcm_offset[1]) <= data_len and pcm_offset[1] - pcm_offset[0] > 0x20:
      decoded = bytearray()
      for byte in data[pcm_offset[0] : pcm_offset[1] + 1]:
        for n in [0,4]:
          nibble = (byte >> n) & 0x0F
          decoded.extend(struct.pack("b", clip_int8((nibble << 3) - 60)))
      pcm = bytearray(audioop.lin2lin(decoded, 1, 2))
      pcm_data.append((pcm, "{:03}".format(i)))
    else:
      pcm_data.append(None)
  return "PPS",pcm_data


#-----------------------------------------------------------------------------
# Extract PCM from "PVI" archive

def extract_pvi(data):
  data_len = len(data)
  if data_len < 0x210: return bad_data()

  # Get offsets
  pcm_offsets = []
  for i in range(128):
    start = end = 0
    if get_uint16(data, i * 4 + 0x12) != 0:
      start =(get_uint16(data, i * 4 + 0x10) << 5)
      end = (get_uint16(data, i * 4 + 0x12) << 5) - 1
    if end < start: end = start
    pcm_offsets.append((start + 0x210, end + 0x210))

  # Get PCM data
  pcm_data = []
  for i,pcm_offset in enumerate(pcm_offsets):
    if (pcm_offset[1]) <= data_len and pcm_offset[1] - pcm_offset[0] > 8:
      pcm = YM_ADPCM.decode(data[pcm_offset[0] : pcm_offset[1]])
      pcm_data.append((pcm, "{:03}".format(i)))
    else:
      pcm_data.append(None)
  return "PVI",pcm_data


#-----------------------------------------------------------------------------
# Extract PCM from "P86" archive

def extract_p86(data):
  data_len = len(data)
  header_len = 16
  if data_len < header_len + 256 * 6 + 2: return bad_data()
  if data_len != get_uint24(data, 0x0D): return bad_data()

  # Get offsets
  pcm_offsets = []
  for i in range(256):
    start = get_uint24(data, header_len + i * 6)
    if start > data_len: return bad_data()
    end = start + get_uint24(data, header_len + 3 + i * 6) - 1
    if end < 0: end = 0
    pcm_offsets.append((start, end))

  # Get PCM data
  pcm_data = []
  for i,pcm_offset in enumerate(pcm_offsets):
    if pcm_offset[0] > 0 and (pcm_offset[1]) <= data_len and pcm_offset[1] - pcm_offset[0] > 0x20:
      pcm = bytearray(audioop.lin2lin(data[pcm_offset[0] : pcm_offset[1] + 1], 1, 2))
      pcm_data.append((pcm, "{:03}".format(i)))
    else:
      pcm_data.append(None)
  return "P86",pcm_data


#-----------------------------------------------------------------------------
# Extract PCM from "P68" archive

def extract_p68(data):
  data_len = len(data)
  if data_len < 256 * 4 + 2: return bad_data()

  # Get offsets
  pcm_offsets = []
  for i in range(256):
    start = get_uint32(data, i * 4, True)
    if start > data_len: return bad_data()
    end = get_uint32(data, 4 + (i * 4), True) - 1
    if i > 0 and get_uint32(data, (i - 1) * 4, True) == data_len:
      pcm_offsets = pcm_offsets[0:-1]
      break
    pcm_offsets.append((start, end))

  # Get PCM data
  pcm_data = []
  for i,pcm_offset in enumerate(pcm_offsets):
    if pcm_offset[1] <= data_len and pcm_offset[1] - pcm_offset[0] > 8:
      pcm = OKI_ADPCM.decode(data[pcm_offset[0] : pcm_offset[1] + 1])
      pcm_data.append((pcm, "{:03}".format(i)))
    else:
      pcm_data.append(None)
  return "P68",pcm_data


#-----------------------------------------------------------------------------
# PMD PCM extraction

def extract_pcm(data, type=None, extension_type=None):
  if type is None:
    ppc_header = bytearray(b'ADPCM DATA for  PMD ver.4.4-  ')
    pvi_header = bytearray(b'PVI2')
    p86_header = bytearray(b'PCM86 DATA')

    if data[0 : len(ppc_header)] == ppc_header:
      type = "PPC"
    elif data[0 : len(pvi_header)] == pvi_header:
      type = "PVI"
    elif data[0 : len(p86_header)] == p86_header:
      type = "P86"
    else:
      type = extension_type

  if type == "PPC":
    return extract_ppc(data)
  elif type == "PPS":
    return extract_pps(data)
  elif type == "PVI":
    return extract_pvi(data)
  elif type == "P86":
    return extract_p86(data)
  elif type == "P68":
    return extract_p68(data)
  else:
    return bad_data()

def bad_data():
  return False,[]


#-----------------------------------------------------------------------------
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
    if len(arguments.infiles) == 0:
      parser.print_help()
      sys.exit(0)

    first = True
    for path in arguments.infiles:
      with open(path, "rb") as infile:

        ext_type = str2type(os.path.splitext(os.path.basename(path))[1])
        type, pcm_data = extract_pcm(bytearray(infile.read()), arguments.type, ext_type)

        if type is None or len(pcm_data) == 0:
          if first is False: print()
          first = False
          print("File '{}' not of recognized type or contains no sample data".format(path))
          continue

        if arguments.verbose:
          if first is False: print()
          print("File:", path)
          print("Type:", type)
          first = False

        gain = arguments.gain
        if type == "P68": gain *= 16.0

        basepath = os.path.abspath(os.path.join(os.path.dirname(path), os.path.basename(path)))
        files_written = 0
        for pcm in pcm_data:
          if pcm is not None:
            outpath = "{}_{}.wav".format(basepath, pcm[1])
            out_pcm = pcm_adjust(pcm[0], gain, arguments.dc_bias_norm)
            wav_write(out_pcm, arguments.sample_rate, outpath)
            if arguments.verbose: print("- {} ({} samples)".format(os.path.basename(outpath), len(pcm[0]) // 2))
            files_written += 1

        if arguments.verbose:
          print("{} samples extracted".format(files_written))

  except IOError as err:
    print("{}".format(err))

if __name__ == "__main__":
    main()
