#!/usr/bin/env python3

# Common functionality

import math
import struct
from collections import namedtuple
import util

# -----------------------------------------------------------------------------
# OPM -> DX7 Voice conversion

# OPM Voice Definition
OPMVoice = namedtuple("OPMVoice", [
    "name",  # Name
    "FL",    # Feedback Level              (3 bits)
    "CON",   # Algorithm                   (3 bits)
    "SLOT",  # Operator & Mod Enable       (8 bits)
    "NE",    # Noise Enable                (1 bit)
    "NFRQ",  # Noise Frequency             (5 bits)
    "AMS",   # Amp Mod Sensitivity         (2 bits)
    "PMS",   # Pitch Mod Sensitivity       (3 bits)
    "LFRQ",  # LFO Frequency               (7 bits)
    "WF",    # LFO Wave Form               (2 bits, 0=Saw, 1=Square, 2=Triangle, 3=Noise)
    "PMD",   # Phase Modulation Depth      (7 bits)
    "AMD",   # Amp Mod Depth               (7 bits)
    "OPM1",  # Operator M1 Parameters      (6 bytes)
    "OPC1",  # Operator C1 Parameters      (6 bytes)
    "OPM2",  # Operator M2 Parameters      (6 bytes)
    "OPC2"   # Operator C2 Parameters      (6 bytes)
])

# OPM Operator Parameters
OPMOP = namedtuple("OPMOP", [
    "TL",    # Total Level                  (7 bits)
    "AR",    # Attack Rate                  (5 bits)
    "D1R",   # Decay Rate 1                 (5 bits)
    "D1L",   # Decay Level 1                (4 bits)
    "D2R",   # Decay Rate 2                 (5 bits)
    "RR",    # Release Rate                 (4 bits)
    "KS",    # Key Scaling                  (2 bits)
    "MUL",   # Phase Multiply               (4 bits)
    "DT1",   # Detune 1 (fine)              (3 bits)
    "DT2",   # Detune 2 (course)            (2 bits)
    "AME"    # Amp Mod Enable               (1 bits)
])

# DX7 Voice Definition
DX7Voice = namedtuple("DX7Voice", [
    "name",  # Name
    "PR1",   # Pitch EG Rate 1             (7 bits, 0-99)
    "PR2",   # Pitch EG Rate 2             (7 bits, 0-99)
    "PR3",   # Pitch EG Rate 3             (7 bits, 0-99)
    "PR4",   # Pitch EG Rate 4             (7 bits, 0-99)
    "PL1",   # Pitch EG Level 1            (7 bits, 0-99)
    "PL2",   # Pitch EG Level 2            (7 bits, 0-99)
    "PL3",   # Pitch EG Level 3            (7 bits, 0-99)
    "PL4",   # Pitch EG Level 4            (7 bits, 0-99)
    "ALG",   # Algorithm                   (5 bits)
    "OKS",   # Oscillator Key Sync         (1 bit)
    "FB",    # Feedback Level              (3 bits)
    "LFS",   # LFO Speed                   (7 bits, 0-99)
    "LFD",   # LFO Delay                   (7 bits, 0-99)
    "LPMD",  # LFO Pitch Mod Depth         (7 bits, 0-99)
    "LAMD",  # LFO Amp Mod Depth           (7 bits, 0-99)
    "LFKS",  # LFO Key Sync                (1 bit)
    "LFW",   # LFO Waveform                (3 bits, 0=Triangle, 1=SawDown, 2=SawUp, 3=Square, 4=Sine, 5=SHold)
    "LPMS",  # LFO Pitch Mod Sensitivity   (3 bits)
    "TRNP",  # Transpose                   (5 bits, 0-48, 12=C2)
    "OPEN",  # Operator Enable             (6 bits, bit0=OP6) (not a register on actual hardware)
    "OP1",   # Operator 1 Parameters
    "OP2",   # Operator 2 Parameters
    "OP3",   # Operator 3 Parameters
    "OP4",   # Operator 4 Parameters
    "OP5",   # Operator 5 Parameters
    "OP6"    # Operator 6 Parameters
])

# DX7 Operator Parameters
DX7OP = namedtuple("DX7OP", [
    "R1",    # EG Rate 1                   (7 bits, 0-99)
    "R2",    # EG Rate 2                   (7 bits, 0-99)
    "R3",    # EG Rate 3                   (7 bits, 0-99)
    "R4",    # EG Rate 4                   (7 bits, 0-99)
    "L1",    # EG Level 1                  (7 bits, 0-99)
    "L2",    # EG Level 2                  (7 bits, 0-99)
    "L3",    # EG Level 3                  (7 bits, 0-99)
    "L4",    # EG Level 4                  (7 bits, 0-99)
    "BP",    # Level Scaling Breakpoint    (7 bits, key)
    "LD",    # Level Scaling Left Depth    (7 bits, 0-99)
    "RD",    # Level Scaling Right Depth   (7 bits, 0-99)
    "LC",    # Level Scaling Left Curve    (2 bits)
    "RC",    # Level Scaling Right Curve   (2 bits)
    "DET",   # Detune (semitones)          (4 bits, 7=normal)
    "RS",    # Key Rate Scaling            (3 bits)
    "AMS",   # Amp Mod Sensitivity         (2 bits)
    "KVS",   # Key Velocity Sensitivity    (3 bits)
    "OL",    # Output Level                (7 bits, 0-99)
    "M",     # Mode (ratio/fixed)          (1 bit, 0=ratio, 1=fixed)
    "FC",    # Frequency (course)          (5 bits)
    "FF"     # Frequency (fine)            (7 bits, 0-99)
])

# Make DX7OP from OPMOP
def OPMOP_to_DX7OP(op, voice, tl_adjustment):
    L2 = [99, 93, 89, 84, 80, 75, 71, 66, 62, 57, 53, 48, 44, 39, 35, 0][op.D1L]
    L3 = 0 if op.D2R != 0 else L2
    return DX7OP(
        R1  = [0, 15, 18, 21, 24, 27, 31, 34, 37, 40, 44, 47, 51, 54, 57, 60, 64, 67, 71, 74, 77, 80, 83, 85, 87, 89, 91, 93, 95, 96, 98, 99][op.AR],
        R2  = [0, 10, 13, 16, 19, 21, 24, 27, 30, 33, 36, 39, 42, 45, 48, 51, 54, 57, 60, 63, 66, 69, 72, 75, 78, 81, 84, 87, 90, 93, 96, 99][op.D1R],
        R3  = [0, 10, 13, 16, 19, 21, 24, 27, 30, 33, 36, 39, 42, 45, 48, 51, 54, 57, 60, 63, 66, 69, 72, 75, 78, 81, 84, 87, 90, 93, 96, 99][op.D2R],
        R4  = [0, 21, 27, 32, 38, 43, 49, 54, 60, 65, 71, 76, 82, 87, 94, 99][op.RR],
        L1  = 99,
        L2  = L2,
        L3  = L3,
        L4  = 0,
        BP  = 0,
        LD  = 0,
        RD  = 0,
        LC  = 0,
        RC  = 0,
        DET = [7, 8, 9, 10, 7, 6, 5, 4][op.DT1],
        RS  = 0,
        AMS = [0, 2, 3, 3][voice.AMS],
        KVS = 0,
        OL  = [98, 97, 96, 95, 94, 93, 92, 91, 90, 89, 88, 87, 86, 85, 84, 83, 82, 81, 80, 79, 78, 77, 76, 75, 74, 73, 72, 71, 70, 69, 68, 67,
               66, 65, 64, 63, 62, 61, 60, 59, 58, 57, 56, 55, 54, 53, 52, 51, 50, 49, 48, 47, 46, 45, 44, 43, 42, 41, 40, 39, 38, 37, 36, 35,
               34, 33, 32, 31, 30, 29, 28, 27, 26, 25, 24, 23, 22, 21, 20, 20, 19, 18, 18, 17, 16, 15, 15, 14, 14, 13, 13, 12, 12, 11, 11, 10,
               10, 9, 9, 8, 8, 7, 7, 6, 6, 5, 5, 5, 4, 4, 4, 4, 3, 3, 3, 3, 2, 2, 2, 2, 1, 1, 1, 1, 0, 0, 0, 0][max(min(op.TL + tl_adjustment, 127), 0)],
        M   = 0,
        FC  = op.MUL,
        FF  = [0, 41, 57, 73][op.DT2]
    )

# Make default DX7OP
def default_DX7OP():
    return DX7OP(
        R1  = 99, R2 = 99, R3 = 99, R4 = 99,
        L1  = 99, L2 = 99, L3 = 90, L4 = 0,
        BP  = 36, LD = 0,  RD = 0,  LC = 0, RC = 0,
        DET = 7, RS = 0,  AMS = 0, KVS = 0,
        OL  = 99, M = 0,   FC = 1,  FF = 0
    )

# Make default ("INIT VOICE") DX7Voice
def default_DX7Voice():
    return DX7Voice(
        name="INIT VOICE",
        PR1  = 50, PR2 = 50, PR3 = 50, PR4 = 50,
        PL1  = 50, PL2 = 50, PL3 = 50, PL4 = 50,
        ALG  = 0,  OKS = 1,  FB = 0,
        LFS  = 0,  LFD = 0,  LPMD = 0, LAMD = 0, LFKS = 0, LFW = 0, LPMS = 0,
        TRNP = 24,
        OPEN = 0x20,
        OP1  = default_DX7OP(), OP2 = default_DX7OP(), OP3 = default_DX7OP(),
        OP4  = default_DX7OP(), OP5 = default_DX7OP(), OP6 = default_DX7OP()
    )

# Make DX7Voice from OPMVoice
def OPMVoice_to_DX7Voice(opmv):
    # Map algorithms
    algorithm_mapping = [0, 13, 7, 6, 4, 21, 30, 31]
    alg = algorithm_mapping[opmv.CON]

    # TL adjustment per OPM algorithm/operator (increase output level of (most) modulators)
    tl_adjustment = [
        [-8, -8, -8, 0],
        [-8, -8, -8, 0],
        [-8, -8, -8, 0],
        [-8, -8, -8, 0],
        [-8, 0, 0, 0],
        [-8, 0, 0, 0],
        [-8, 0, 0, 0],
        [0, 0, 0, 0],
    ]

    # Convert operators
    op6 = OPMOP_to_DX7OP(opmv.OPM1, opmv, tl_adjustment[opmv.CON][0])
    op5 = OPMOP_to_DX7OP(opmv.OPC1, opmv, tl_adjustment[opmv.CON][1])
    op4 = OPMOP_to_DX7OP(opmv.OPM2, opmv, tl_adjustment[opmv.CON][2])
    op3 = OPMOP_to_DX7OP(opmv.OPC2, opmv, tl_adjustment[opmv.CON][3])

    # Re-order operators for algorithms lacking a 1:1 match
    if opmv.CON == 2:
        op4, op5, op6 = op6, op4, op5

    return DX7Voice(
        name = opmv.name[:10],
        PR1  = 50, PR2 = 50, PR3 = 50, PR4 = 50,
        PL1  = 50, PL2 = 50, PL3 = 50, PL4 = 50,
        ALG  = alg,
        OKS  = 0,
        FB   = opmv.FL,
        LFS  = util.int_remap(opmv.LFRQ, (0, 127), (0, 99)),
        LFD  = 0,
        LPMD = util.int_remap(opmv.PMD, (0, 127), (0, 99)),
        LAMD = util.int_remap(opmv.AMD, (0, 127), (0, 99)),
        LFKS = 0,
        LFW  = [2, 3, 0, 5][opmv.WF],
        LPMS = opmv.PMS,
        TRNP = 24,
        OPEN = 0x0F & opmv.SLOT,
        OP6  = op6, OP5 = op5, OP4 = op4, OP3 = op3,
        OP2  = default_DX7OP(), OP1 = default_DX7OP()
    )

# Make "BULK data" DX7 voice definition
def packed_DX7Voice(v):
    p = bytearray()
    # Add operator definitions
    for i, op in enumerate([v.OP6, v.OP5, v.OP4, v.OP3, v.OP2, v.OP1]):
        p.extend([op.R1, op.R2, op.R3, op.R4, op.L1, op.L2, op.L3, op.L4])
        p.extend([op.BP, op.LD, op.RD])
        p.append(((op.RC << 2) & 0x0C) | (op.LC & 0x03))
        p.append(((min(op.DET, 14) << 3) & 0x78) | (op.RS & 0x07))
        p.append(((op.KVS << 2) & 0x1C) | (op.AMS & 0x03))
        # Operator enabled / disabled
        if v.OPEN & (1 << i) != 0:
            p.append(op.OL)
        else:
            p.append(0x00)
        p.append(((op.FC << 1) & 0x3E) | (op.M & 0x01))
        p.append(op.FF)
    # Add voice settings
    p.extend([v.PR1, v.PR2, v.PR3, v.PR4, v.PL1, v.PL2, v.PL3, v.PL4, v.ALG])
    p.append(((v.OKS << 4) & 0x10) | (v.FB & 0x07))
    p.extend([v.LFS, v.LFD, v.LPMD, v.LAMD])
    p.append(((v.LPMS << 4) & 0x70) | ((v.LFW << 1) & 0x0E) | (v.LFKS & 0x01))
    p.append(v.TRNP & 0x1F)
    p.extend(bytearray((v.name.ljust(10))[:10].encode("ascii")))
    # Make sure it's valid sysex by stripping bit 7
    return bytearray(map(lambda x: x & 0x7F, p))

# Make DX7 "32 voice BULK data" sysex message
def sysex_from_DX7Voices(dx7vs):
    # Pad with default voice data
    for _ in range(len(dx7vs), 32):
        dx7vs.append(default_DX7Voice())
    # Get packed voice definitions
    data = bytearray()
    for v in dx7vs[:32]:
        data.extend(packed_DX7Voice(v))
    # Finalize sysex message
    syx = bytearray()
    syx.extend(bytearray([0xF0, 0x43, 0x00, 0x09, 0x20, 0x00]))
    syx.extend(data)
    syx.append(((~sum(data)) + 1) & 0x7F)
    syx.append(0xF7)
    return syx


#-----------------------------------------------------------------------------
# Yamaha "DELTA-T" ADPCM decoder

class YM_ADPCM(object):
    diff_lut = [ 1,  3,  5,  7,  9, 11, 13, 15,  -1, -3, -5, -7, -9,-11,-13,-15]
    step_lut = [57, 57, 57, 57, 77,102,128,153,  57, 57, 57, 57, 77,102,128,153]
    step_max = 24576
    step_min = 127

    @staticmethod
    def decode(data):
        decoded = bytearray()
        signal =  0
        step = 127
        for nibble in util.nibbles(data, True):
            signal += (step * YM_ADPCM.diff_lut[nibble]) / 8
            signal = util.clip_int16(signal)
            step = (step * YM_ADPCM.step_lut[nibble]) / 64
            step = util.clip_int(step, YM_ADPCM.step_min, YM_ADPCM.step_max)
            decoded.extend(struct.pack("<h", signal))
        return decoded


# -----------------------------------------------------------------------------
# OKI MSM6258V ADPCM decoder

class OKI_ADPCM():
    @staticmethod
    def make_diff_lut():
        bitmap = [
            [1, 0, 0, 0], [1, 0, 0, 1], [1, 0, 1, 0], [1, 0, 1, 1],
            [1, 1, 0, 0], [1, 1, 0, 1], [1, 1, 1, 0], [1, 1, 1, 1],
            [-1, 0, 0, 0], [-1, 0, 0, 1], [-1, 0, 1, 0], [-1, 0, 1, 1],
            [-1, 1, 0, 0], [-1, 1, 0, 1], [-1, 1, 1, 0], [-1, 1, 1, 1]
        ]
        diff_lut = [0] * (49 * 16)
        for step in range(49):
            stepval = int(math.floor(16.0 * pow(11.0 / 10.0, float(step))))
            for n in range(16):
                diff_lut[step * 16 + n] = bitmap[n][0] * (
                    stepval * bitmap[n][1] + stepval // 2 * bitmap[n][2] + stepval // 4 * bitmap[n][3] + stepval // 8)
        return diff_lut

    diff_lut = make_diff_lut.__func__()
    step_lut = [-1, -1, -1, -1, 2, 4, 6, 8, -1, -1, -1, -1, 2, 4, 6, 8]
    step_max = 48
    step_min = 0

    @staticmethod
    def decode(data):
        decoded = bytearray()
        signal = -2
        step = 0
        for nibble in util.nibbles(data, False):
            signal += OKI_ADPCM.diff_lut[step * 16 + nibble]
            signal = util.clip_int16(signal)
            step += OKI_ADPCM.step_lut[nibble]
            step = util.clip_int(step, OKI_ADPCM.step_min, OKI_ADPCM.step_max)
            decoded.extend(struct.pack("<h", signal))
        return decoded


# -----------------------------------------------------------------------------
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


# -----------------------------------------------------------------------------
# Add gain and adjust DC offset

def pcm_adjust(pcm, gain=1, fix_dc_offset=True):
    if len(pcm) % 2:
        return pcm

    dc_bias = 0
    if fix_dc_offset is True:
        summ = 0
        for i in range(len(pcm) // 2):
            summ += struct.unpack("<h", pcm[i * 2: i * 2 + 2])[0]
        dc_bias = summ // (len(pcm) // 2)

    adjusted = bytearray()
    for i in range(len(pcm) // 2):
        val = struct.unpack("<h", pcm[i * 2: i * 2 + 2])[0]
        adjusted.extend(struct.pack("<h", util.clip_int16((val - dc_bias) * gain)))
    return adjusted
