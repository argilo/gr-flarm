#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2014 Clayton Smith.
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

import numpy
import struct
from gnuradio import gr
from datetime import datetime


def xtea_decrypt(key,block,n=32,endian="!"):
    """
        Decrypt 64 bit data block using XTEA block cypher
        * key = 128 bit (16 char)
        * block = 64 bit (8 char)
        * n = rounds (default 32)
        * endian = byte order (see 'struct' doc - default big/network)

        >>> z = 'b67c01662ff6964a'.decode('hex')
        >>> xtea_decrypt('0123456789012345',z)
        'ABCDEFGH'

        Only need to change byte order if sending/receiving from
        alternative endian implementation

        >>> z = 'ea0c3d7c1c22557f'.decode('hex')
        >>> xtea_decrypt('0123456789012345',z,endian="<")
        'ABCDEFGH'

    """
    v0,v1 = struct.unpack(endian+"2L",block)
    k = struct.unpack(endian+"4L",key)
    delta,mask = 0x9e3779b9L,0xffffffffL
    sum = (delta * n) & mask
    for round in range(n):
        v1 = (v1 - (((v0<<4 ^ v0>>5) + v0) ^ (sum + k[sum>>11 & 3]))) & mask
        sum = (sum - delta) & mask
        v0 = (v0 - (((v1<<4 ^ v1>>5) + v1) ^ (sum + k[sum & 3]))) & mask
    return struct.pack(endian+"2L",v0,v1)


class packetize(gr.basic_block):
    """
    docstring for block packetize
    """

    # 0011 0001 1111 1010 1011 0110
    sync_word = numpy.array([0,1, 0,1, 1,0, 1,0, 0,1, 0,1, 0,1, 1,0, 1,0, 1,0, 1,0, 1,0, 1,0, 0,1, 1,0, 0,1, 1,0, 0,1, 1,0, 1,0, 0,1, 1,0, 1,0, 0,1],dtype=numpy.int8).tostring()

    key1 = struct.pack(">4L", 0x58C1FA95, 0x26DACE48, 0xFF34088C, 0xA47564E2)
    key2 = struct.pack(">4L", 0x211D5B80, 0x5230C9CD, 0x8BA2EF63, 0x13D7BE02)

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
            in_sig=[numpy.int8]*num_channels,
            out_sig=[numpy.int8])
        self.first_channel = first_channel
        self.rxid = rxid
        self.reflat = int(reflat * 1e7)
        self.reflon = int(reflon * 1e7)

    def forecast(self, noutput_items, ninput_items_required):
        for channel in range(len(ninput_items_required)):
            ninput_items_required[channel] = 5000

    def manchester_demod_packet(self, channel, man_bits):
        for x in range(0, len(man_bits), 2):
            if man_bits[x] == man_bits[x+1]:
                # Manchester error. Discard packet.
                return ""
        else:
            # We've got a valid packet! Throw out the preamble and SFD
            # and extract the bits from the Manchester encoding.
            return self.process_packet(channel, man_bits[0::2])

    def process_packet(self, channel, bits):
        bytes = numpy.packbits(bits)
        if self.crc16(bytes) != 0:
            # Invalid CRC
            print "Invalid CRC!"
            return ""
        else:
            raw_hex = "".join(["{0:02x}".format(byte) for byte in bytes])
            bytes = self.decrypt_packet(bytes)
            icao, lat, lon, alt, vs, stealth, typ, ns, ew = self.extract_values(bytes[3:27])

            lat = self.recover_lat(lat)
            lon = self.recover_lon(lat, lon)

            print datetime.now().isoformat(),
            print "Ch.{0:02}".format(channel),
            #print "{0:02x}{1:02x}{2:02x}".format(*bytes[0:3]),
            print "ICAO: " + icao,
            print "Lat: " + str(lat),
            print "Lon: " + str(lon),
            print "Alt: " + str(alt) + "m",
            print "VS: " + str(vs),
            print "Stealth: " + str(stealth),
            print "Type: " + str(typ),
            print "North/South speeds: {0},{1},{2},{3}".format(*ns),
            print "East/West speeds: {0},{1},{2},{3}".format(*ew),
            print "Raw: {0:02x}".format(bytes[6]),
            print "{0:02x}{1:02x}{2:02x}{3:02x}{4:02x}{5:02x}{6:02x}{7:02x}".format(*bytes[7:15]),
            print "{0:02x}{1:02x}{2:02x}{3:02x}{4:02x}{5:02x}{6:02x}{7:02x}".format(*bytes[15:23]),
            print "{0:02x}{1:02x}{2:02x}{3:02x}".format(*bytes[23:27]),
            #print "{0:02x}{1:02x}".format(*bytes[27:29]),
            if icao in self.icao_table:
                reg, typ, tail = self.icao_table[icao]
                print "(Reg: " + reg + ", Type: " + typ + ", Tail: " + tail + ")",
            print

            packet_data = ["$FLM", datetime.now().isoformat(), self.rxid, str(channel), icao, str(lat), str(lon), str(alt), raw_hex]
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

    def decrypt_packet(self, bytes):
        block = xtea_decrypt(self.key1, struct.pack("<2L", (bytes[7] << 24) | (bytes[8] << 16) | (bytes[9] << 8) | bytes[10], (bytes[11] << 24) | (bytes[12] << 16) | (bytes[13] << 8) | bytes[14]), n=6)
        for i in range(4):
            bytes[10-i] = ord(block[i])
            bytes[14-i] = ord(block[i+4])
        block = xtea_decrypt(self.key2, struct.pack("<2L", (bytes[15] << 24) | (bytes[16] << 16) | (bytes[17] << 8) | bytes[18], (bytes[19] << 24) | (bytes[20] << 16) | (bytes[21] << 8) | bytes[22]), n=6)
        for i in range(4):
            bytes[18-i] = ord(block[i])
            bytes[22-i] = ord(block[i+4])
        return bytes

    def extract_values(self, bytes):
        icao = "{0:02x}{1:02x}{2:02x}".format(bytes[2], bytes[1], bytes[0])
        lat = (bytes[5] << 8) | bytes[4]
        lon = (bytes[7] << 8) | bytes[6]
        alt = ((bytes[9] & 0x1f) << 8) | bytes[8]
        vs = ((bytes[10] & 0x7f) << 3) | ((bytes[9] & 0xe0) >> 5)
        vsmult = ((bytes[21] & 0xc0) >> 6)
        if vs < 0x200:
            vs = (vs << vsmult)
        else:
            vs -= 0x400
        stealth = ((bytes[11] & 0x80) == 0x80)
        typ = ((bytes[11] & 0x3C) >> 2)
        ns = [b if b < 0x80 else (b - 0x100) for b in bytes[12:16]]
        ew = [b if b < 0x80 else (b - 0x100) for b in bytes[16:20]]
        return icao, lat, lon, alt, vs, stealth, typ, ns, ew

    def recover_lat(self, recv_lat):
        round_lat = self.reflat >> 7
        lat = (recv_lat - round_lat) % 0x10000
        if lat >= 0x8000: lat -= 0x10000
        lat = ((lat + round_lat) << 7) + 0x40
        return lat

    def recover_lon(self, lat, recv_lon):
        shift = 8 if lat >= 450000000 else 7
        round_lon = self.reflon >> shift
        lon = (recv_lon - round_lon) % 0x10000
        if lon >= 0x8000: lon -= 0x10000
        lon = ((lon + round_lon) << shift) + (1 << (shift-1))
        return lon

    def general_work(self, input_items, output_items):
        # Wait until we get at least one packet worth of Manchester bits
        if len(input_items[0]) < 464:
            return 0

        output = ""
        for channel in range(len(input_items)):
            index = input_items[channel].tostring().find(self.sync_word, 0, -464+48)
            while index != -1:
                output = output + self.manchester_demod_packet(channel + self.first_channel, input_items[channel][index:index+464])
                index = input_items[channel].tostring().find(self.sync_word, index+464, -464+48)
            self.consume(channel, len(input_items[channel])-463)

        output = numpy.array([ord(c) for c in output], dtype=numpy.int8)
        output_items[0][0:len(output)] = output
        return len(output)
