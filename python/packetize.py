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
from gnuradio import gr
from datetime import datetime

class packetize(gr.basic_block):
    """
    docstring for block packetize
    """

    # 0000 1100 1001 1010 1001 0011
    sync_word = numpy.array([0,1, 0,1, 0,1, 0,1, 1,0, 1,0, 0,1, 0,1, 1,0, 0,1, 0,1, 1,0, 1,0, 0,1, 1,0, 0,1, 1,0, 0,1, 0,1, 1,0, 0,1, 0,1, 1,0, 1,0],dtype=numpy.int8).tostring()

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
        "c06b5f": ("C-GORE", "PIK20", "GP")
    }

    def __init__(self):
        gr.basic_block.__init__(self,
            name="packetize",
            in_sig=[numpy.int8],
            out_sig=[])

    def forecast(self, noutput_items, ninput_items_required):
        ninput_items_required[0] = 5000

    def manchester_demod_packet(self, man_bits):
        for x in range(0, len(man_bits), 2):
            if man_bits[x] == man_bits[x+1]:
                # Manchester error. Discard packet.
                break
        else:
            # We've got a valid packet! Throw out the preamble and SFD
            # and extract the bits from the Manchester encoding.
            self.process_packet(man_bits[0::2])

    def process_packet(self, bits):
        bytes = numpy.packbits(bits)
        if self.crc16(bytes) == 0:
            print "    Time: " + datetime.now().isoformat()
            #print "   Sync: {0:02x}{1:02x}{2:02x}".format(*bytes[0:3])
            icao = "{0:02x}{1:02x}{2:02x}".format(bytes[5], bytes[4], bytes[3])
            if icao in self.icao_table:
                reg, typ, tail = self.icao_table[icao]
                print "    ICAO: " + icao + " (Reg: " + reg + ", Type: " + typ + ", Tail: " + tail + ")"
            else:
                print "    ICAO: " + icao
            print " Unknown: {0:02x}".format(bytes[6])
            print "Cipher 1: {0:02x}{1:02x}{2:02x}{3:02x}{4:02x}{5:02x}{6:02x}{7:02x}".format(*bytes[7:15])
            print "Cipher 2: {0:02x}{1:02x}{2:02x}{3:02x}{4:02x}{5:02x}{6:02x}{7:02x}".format(*bytes[15:23])
            print " Unknown: {0:02x}{1:02x}{2:02x}{3:02x}".format(*bytes[23:27])
            #print "    CRC: {0:02x}{1:02x}".format(*bytes[27:29])
            print

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

    def general_work(self, input_items, output_items):
        # Wait until we get at least one packet worth of Manchester bits
        if len(input_items[0]) < 464:
            self.consume(0, 0)
            return 0

        index = input_items[0].tostring().find(self.sync_word, 0, -464+48)
        while index != -1:
            self.manchester_demod_packet(input_items[0][index:index+464])
            index = input_items[0].tostring().find(self.sync_word, index+464, -464+48)

        self.consume(0, len(input_items[0])-463)
        return 0
