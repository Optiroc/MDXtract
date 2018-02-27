#!/usr/local/bin/python3

# pdxtract
#
# Utility to extract and convert sample data from PDX file.
# PDX is the sample archive format used by MXDRV, a popular
# sound driver for the Sharp X68000 computer. The 4 bits per
# sample ADPCM data is converted to 16 bit uncompressed PCM.
#
# Usage:
# pdxtract.py [-h, --help] [infiles ...]
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
# PDX parser

def get_uint32(bytes, offset):
  return (bytes[offset] << 24) + (bytes[offset + 1] << 16) + (bytes[offset + 2] << 8) + bytes[offset + 3]

class PDX(object):
  def __init__(self, bytes):
    # Get PCM offsets,lengths
    self.pcm_offsets = []
    filesize = len(bytes)
    for i in range(96):
      pcm_offset = (get_uint32(bytes, i * 8), get_uint32(bytes, 4 + (i * 8)))
      self.pcm_offsets.append(pcm_offset)

    # Get PCM data
    self.pcm_data = []
    for pcm_offset in self.pcm_offsets:
      if pcm_offset[1] > 1 and (pcm_offset[0] + pcm_offset[1]) <= filesize:
        self.pcm_data.append(bytes[pcm_offset[0] : pcm_offset[0] + pcm_offset[1]])
      else:
        self.pcm_data.append(None)


#-----------------------------------------------------------------------------
# ADPCM decoder

class ADPCM(object):
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
  signal_max = int((1 << (16 - 1)) - 1)
  signal_min = int(-(1 << (16 - 1)))

  def decode(data):
    decoded = bytearray()
    signal = -2;
    step = 0;
    for byte in data:
      for nybble in range(2):
        # Add delta
        sample = (byte >> (nybble << 2)) & 0x0F
        signal += ADPCM.diff_lut[step * 16 + sample]
        if signal > ADPCM.signal_max: signal = ADPCM.signal_max
        elif signal < ADPCM.signal_min: signal = ADPCM.signal_min
        # Add step
        step += ADPCM.step_lut[sample];
        if step > ADPCM.step_max: step = ADPCM.step_max
        elif step < ADPCM.step_min: step = ADPCM.step_min
        # Add gain
        output = signal << 4
        if output > ADPCM.signal_max: output = ADPCM.signal_max
        elif output < ADPCM.signal_min: output = ADPCM.signal_min
        decoded.extend(struct.pack("<h", output))
    return decoded


#-----------------------------------------------------------------------------
# WAV writer

def wav_write(data, path):
  sample_rate = 16000
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
# Command Line Interface

def main():
  parser = argparse.ArgumentParser()
  parser.add_argument("infiles", nargs="*", help="input file(s)")

  try:
    arguments = parser.parse_args()

    for path in arguments.infiles:
      with open(path, "rb") as infile:
        basepath = os.path.abspath(os.path.join(os.path.dirname(path), os.path.splitext(os.path.basename(path))[0]))
        pdx = PDX(bytearray(infile.read()))
        for index, pcm in enumerate(pdx.pcm_data, 1):
          if pcm is not None:
            outpath = "{}_{:02}.wav".format(basepath, index)
            wav_write(ADPCM.decode(pcm), outpath)

  except IOError as err:
    print("{}".format(err))

if __name__ == "__main__":
    main()
