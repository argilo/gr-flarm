#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 
# Copyright 2014 <+YOU OR YOUR COMPANY+>.
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

class packetize(gr.basic_block):
    """
    docstring for block packetize
    """

    # 0101 0000 1100 1001
    sync_word = numpy.array([0,1, 1,0, 0,1, 1,0, 0,1, 0,1, 0,1, 0,1, 1,0, 1,0, 0,1, 0,1, 1,0, 0,1, 0,1, 1,0],dtype=numpy.int8).tostring()

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
        print bits.tostring().replace("\x00","0").replace("\x01","1")

    def general_work(self, input_items, output_items):
        # Wait until we get at least one packet worth of Manchester bits
        if len(input_items[0]) < 472:
            self.consume(0, 0)
            return 0

        index = input_items[0].tostring().find(self.sync_word, 0, -472+32)
        while index != -1:
            self.manchester_demod_packet(input_items[0][index:index+472])
            index = input_items[0].tostring().find(self.sync_word, index+472, -472+32)

        self.consume(0, len(input_items[0])-471)
        return 0
