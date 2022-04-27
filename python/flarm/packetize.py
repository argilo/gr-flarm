#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2014,2015,2020 Clayton Smith.
#
# This is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
#
# This software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this software; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.
#

from __future__ import print_function

import numpy
import struct
from gnuradio import gr
from datetime import datetime
import time


def u32(x):
    return x & 0xffffffff

def obscure_key(key, seed):
    m1 = u32(seed * (key ^ (key >> 16)))
    m2 = u32(seed * (m1 ^ (m1 >> 16)))
    return m2 ^ (m2 >> 16)

def make_key(time, address):
    if (time >> 27) & 4 == 0:
        table = [ 0xe43276df, 0xdca83759, 0x9802b8ac, 0x4675a56b ]
    else:
        table = [ 0xfc78ea65, 0x804b90ea, 0xb76542cd, 0x329dfa32 ]
    return [obscure_key(word ^ ((time>>6) ^ address), 0x045D9F3B) ^ 0x87B562F4 for word in table]

# Adapted from https://github.com/andersekbom/prycut/blob/master/pyxxtea.py
#
# Pure Python (2.x) implementation of the XXTEA cipher
# (c) 2009. Ivan Voras <ivoras@gmail.com>
# Released under the BSD License.
#
def raw_xxtea(v, n, k):
    def MX():
        return ((z>>5)^(y<<2)) + ((y>>3)^(z<<4))^(sum^y) + (k[(p & 3)^e]^z)

    y = v[0]
    sum = 0
    DELTA = 0x9e3779b9
    if n > 1:       # Encoding
        z = v[n-1]
        q = 6 # + 52 / n
        while q > 0:
            q -= 1
            sum = u32(sum + DELTA)
            e = u32(sum >> 2) & 3
            p = 0
            while p < n - 1:
                y = v[p+1]
                z = v[p] = u32(v[p] + MX())
                p += 1
            y = v[0]
            z = v[n-1] = u32(v[n-1] + MX())
        return 0
    elif n < -1:    # Decoding
        n = -n
        q = 6 # + 52 / n
        sum = u32(q * DELTA)
        while sum != 0:
            e = u32(sum >> 2) & 3
            p = n - 1
            while p > 0:
                z = v[p-1]
                y = v[p] = u32(v[p] - MX())
                p -= 1
            z = v[n-1]
            y = v[0] = u32(v[0] - MX())
            sum = u32(sum - DELTA)
        return 0
    return 1


class packetize(gr.basic_block):
    """
    docstring for block packetize
    """

    # 0011 0001 1111 1010 1011 0110
    sync_word = numpy.array([0,1, 0,1, 1,0, 1,0, 0,1, 0,1, 0,1, 1,0, 1,0, 1,0, 1,0, 1,0, 1,0, 0,1, 1,0, 0,1, 1,0, 0,1, 1,0, 1,0, 0,1, 1,0, 1,0, 0,1],dtype=numpy.int8).tostring()

    icao_table = {
        "c06edf": ("C-GPZQ", "LS4",   "84"),
        "c02487": ("C-FNVQ", "ASW20", "VQ"),
        "c003b6": ("C-GBKN", "ASW20", "MZ"),
        "c081b6": ("C-GXDD", "SZD55", "2D"),
        "c06914": ("C-GNUP", "SZD55", "55"),
        "c0789b": ("C-GTRM", "ASW20", "RM"),
        "c05fdd": ("C-GKHU", "ASW24", "M7"),
        "c06208": ("C-GLDF", "LAK12", "Z7"),
        "c007be": ("C-FCYF", "SZD55", "AT"),
        "c06b5f": ("C-GORE", "PIK20", "GP"),
        "dd8223": ("PH-1431", "DG1000", "GO1"),
        "dd8202": ("PH-1432", "DG1000", "GO2"),
        "dddefb": ("PH-1489", "DUOD", "GO3")
    }

    def __init__(self, num_channels, first_channel, rxid, reflat, reflon):
        gr.basic_block.__init__(self,
            name="packetize",
            in_sig=[numpy.int8,]*num_channels,
            out_sig=[numpy.int8,])
        self.first_channel = first_channel
        self.rxid = rxid
        self.reflat = int(reflat * 1e7)
        self.reflon = int(reflon * 1e7)

    def forecast(self, noutput_items, ninputs):
        return [5000] * ninputs

    def manchester_demod_packet(self, channel, man_bits, time):
        for x in range(0, len(man_bits), 2):
            if man_bits[x] == man_bits[x+1]:
                # Manchester error. Discard packet.
                return ""
        else:
            # We've got a valid packet! Throw out the preamble and SFD
            # and extract the bits from the Manchester encoding.
            return self.process_packet(channel, man_bits[0::2], time)

    MAX_OFFSET = 50
    def time_offsets(self, estimate):
        yield estimate
        for offset in range(1, self.MAX_OFFSET + abs(estimate) + 1):
            if estimate + offset <= self.MAX_OFFSET: yield estimate + offset
            if estimate - offset >= -self.MAX_OFFSET: yield estimate - offset

    last_offset = 0
    def process_packet(self, channel, bits, time):
        in_bytes = numpy.packbits(bits)
        if self.crc16(in_bytes) != 0:
            print("Invalid CRC!")
            return ""

        raw_hex = "".join(["{0:02x}".format(byte) for byte in in_bytes])
        if in_bytes[6] == 0x10:
            for offset in self.time_offsets(self.last_offset):
                key = make_key(int(time) + offset*64, (in_bytes[4] << 16) | (in_bytes[3] << 8))
                bytes = self.decrypt_packet(in_bytes, key)
                icao, lat, lon, alt, vs, no_track, stealth, typ, ns, ew, status, unk = self.extract_values(bytes[3:27])
                if unk in [0x0000, 0x0400, 0x1000, 0x1400]:
                    print("Time offset: " + str(offset*64), end=" ")
                    self.last_offset = offset

                    lat = self.recover_lat(lat)
                    lon = self.recover_lon(lon)

                    print(datetime.utcfromtimestamp(time).isoformat() + 'Z', end=" ")
                    print("Ch.{0:02}".format(channel), end=" ")
                    print("ICAO: " + icao, end=" ")
                    print("Lat: " + str(lat), end=" ")
                    print("Lon: " + str(lon), end=" ")
                    print("Alt: " + str(alt) + "m", end=" ")
                    print("VS: " + str(vs), end=" ")
                    print("No-track: " + str(no_track), end=" ")
                    print("Stealth: " + str(stealth), end=" ")
                    print("Type: " + str(typ), end=" ")
                    print("GPS status: " + str(status), end=" ")
                    print("North/South speeds: {0},{1},{2},{3}".format(*ns), end=" ")
                    print("East/West speeds: {0},{1},{2},{3}".format(*ew), end=" ")
                    print("Unknown: {0:04x}".format(unk), end=" ")
                    print("Raw: {0:02x}".format(bytes[6]), end=" ")
                    print("{0:02x}{1:02x}{2:02x}{3:02x}{4:02x}{5:02x}{6:02x}{7:02x}".format(*bytes[7:15]), end=" ")
                    print("{0:02x}{1:02x}{2:02x}{3:02x}{4:02x}{5:02x}{6:02x}{7:02x}".format(*bytes[15:23]), end=" ")
                    print("{0:02x}{1:02x}{2:02x}{3:02x}".format(*bytes[23:27]), end=" ")
                    if icao in self.icao_table:
                        reg, typ, tail = self.icao_table[icao]
                        print("(Reg: " + reg + ", Type: " + typ + ", Tail: " + tail + ")", end=" ")
                    print()

                    break
            else:
                print("Couldn't decrypt packet!")
                icao, _, _, _, _, _, _, _, _, _, _, _ = self.extract_values(in_bytes[3:27])
                lat, lon, alt = -1, -1, -1

        else:
            print("Don't know how to decrypt packet type {0:02x}".format(in_bytes[6]))
            icao, _, _, _, _, _, _, _, _, _, _, _ = self.extract_values(in_bytes[3:27])
            lat, lon, alt = -1, -1, -1


        packet_data = ["$FLM", datetime.utcfromtimestamp(time).isoformat() + 'Z', self.rxid, str(channel), icao, str(lat), str(lon), str(alt), raw_hex]
        return ",".join(packet_data) + "\r\n"

    def crc16(self, message):
        poly = 0x1021
        reg = 0xffff
        for byte in message:
            mask = 0x80
            while mask != 0:
                reg <<= 1
                if byte & mask:
                    reg ^= 1
                mask >>= 1
                if reg & 0x10000 != 0:
                    reg &= 0xffff
                    reg ^= poly
        reg ^= 0x9335
        return reg

    def decrypt_packet(self, bytes, key):
        v = []
        result = list(bytes)
        for x in range(5):
            v.append((bytes[4*x+10] << 24) | (bytes[4*x+9] << 16) | (bytes[4*x+8] << 8) | bytes[4*x+7])
        raw_xxtea(v, -5, key)
        for x in range(5):
            result[4*x+10]  =  v[x] >> 24
            result[4*x+9]  = (v[x] >> 16) & 0xff
            result[4*x+8]  = (v[x] >> 8) & 0xff
            result[4*x+7] =  v[x] & 0xff
        return result

    def extract_values(self, bytes):
        icao = "{0:02x}{1:02x}{2:02x}".format(bytes[2], bytes[1], bytes[0])
        vs = ((bytes[5] & 0b00000011) << 8) | bytes[4]
        status = ((bytes[7] & 0b00001111) << 8) | bytes[6]
        typ = ((bytes[7] & 0b11110000) >> 4)
        lat = ((bytes[10] & 0b00000111) << 16) | (bytes[9] << 8) | bytes[8]
        lon = ((bytes[14] & 0b00001111) << 16) | (bytes[13] << 8) | bytes[12]
        alt = (bytes[11] << 5) | ((bytes[10] & 0b11111000) >> 3)
        vsmult = ((bytes[15] & 0b11000000) >> 6)
        if vs < 0x200:
            vs = (vs << vsmult)
        else:
            vs -= 0x400
        no_track = bool(bytes[5] & 0b01000000)
        stealth  = bool(bytes[5] & 0b00100000)
        ns = [b if b < 0x80 else (b - 0x100) for b in bytes[16:20]]
        ew = [b if b < 0x80 else (b - 0x100) for b in bytes[20:24]]
        unk = ((bytes[5] & 0b00011100) << 8) | ((bytes[14] & 0b11110000) << 2) | (bytes[15] & 0b00111111)
        return icao, lat, lon, alt, vs, no_track, stealth, typ, ns, ew, status, unk

    def recover_lat(self, recv_lat):
        round_lat = self.reflat >> 7
        lat = (recv_lat - round_lat) % 0x80000
        if lat >= 0x40000: lat -= 0x80000
        lat = ((lat + round_lat) << 7) + 0x40
        return lat

    def recover_lon(self, recv_lon):
        round_lon = self.reflon >> 7
        lon = (recv_lon - round_lon) % 0x100000
        if lon >= 0x80000: lon -= 0x100000
        lon = ((lon + round_lon) << 7) + 0x40
        return lon

    def general_work(self, input_items, output_items):
        # Wait until we get at least one packet worth of Manchester bits
        if len(input_items[0]) < 464:
            return 0

        output = ""
        for channel in range(len(input_items)):
            index = input_items[channel].tostring().find(self.sync_word, 0, -464+48)
            while index != -1:
                output = output + self.manchester_demod_packet(channel + self.first_channel, input_items[channel][index:index+464], time.time())
                index = input_items[channel].tostring().find(self.sync_word, index+464, -464+48)
            self.consume(channel, len(input_items[channel])-463)

        output = numpy.array([ord(c) for c in output], dtype=numpy.int8)
        output_items[0][0:len(output)] = output
        return len(output)

if __name__ == "__main__":
    import sys
    import dateutil.parser
    import pytz

    def iso_to_unix(datetime_string):
        dt = dateutil.parser.parse(datetime_string)
        if dt.tzinfo == None:
            dt = pytz.timezone('US/Eastern').localize(dt)
        epoch = datetime(1970, 1, 1, tzinfo=pytz.UTC)
        return (dt - epoch).total_seconds()

    def hex_to_bits(hex_string):
        bytes = []
        for x in range(0, len(hex_string), 2):
            bytes.append(int(hex_string[x:x+2], 16))
        bytes = numpy.array(bytes, dtype=numpy.uint8)
        return numpy.unpackbits(bytes)

    if len(sys.argv) < 2:
        print("Usage: packetize.py <filename>")
        exit(1)

    with open(sys.argv[1]) as f:
        p = packetize(1, 0, "00", 45.10513, -75.623744)
        for line in f:
            fields = line.rstrip().split(',')
            time, bits = iso_to_unix(fields[1]), hex_to_bits(fields[8])
            result = p.process_packet(0, bits, time)
            print(result.rstrip())
