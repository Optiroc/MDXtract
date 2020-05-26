#!/usr/bin/env python3

# Utility functions

# -----------------------------------------------------------------------------
def clip_int(value, min_value, max_value):
    return int(max(min_value, min(value, max_value)))

def clip_int16(value):
    return int(max(-32768, min(value, 32767)))

def clip_int8(value):
    return int(max(-128, min(value, 127)))

# -----------------------------------------------------------------------------
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

# -----------------------------------------------------------------------------
def nibbles(data, big_endian=False):
    shift = [0, 4] if not big_endian else [4, 0]
    for byte in data:
        for s in shift:
            yield (byte >> s) & 0x0F

# -----------------------------------------------------------------------------
# Remap n from range r1(min,max) to range r2(min,max)
def remap(n, r1, r2):
    r1_min = min(r1[0], r1[1])
    r1_max = max(r1[0], r1[1])
    r2_min = min(r2[0], r2[1])
    r2_max = max(r2[0], r2[1])
    r1_reverse = r1_min != r1[0]
    r2_reverse = r2_min != r2[0]
    offset = (r1_max - n) * (r2_max - r2_min) / (r1_max -
                                                 r1_min) if r1_reverse else (n - r1_min) * (r2_max - r2_min) / (r1_max - r1_min)
    return r2_max - offset if r2_reverse else r2_min + offset

def int_remap(n, r1, r2):
    return int(round(remap(n, r1, r2)))
