# -*- coding: utf-8 -*-

#
# SPDX-License-Identifier: GPL-3.0
#
# GNU Radio Python Flow Graph
# Title: 1-Ch Rx
# GNU Radio version: v3.11.0.0git-46-g614681ba

from gnuradio import analog
import math
from gnuradio import digital
from gnuradio import gr
from gnuradio.filter import firdes
from gnuradio.fft import window
import sys
import signal







class flarm_channel_rx(gr.hier_block2):
    def __init__(self):
        gr.hier_block2.__init__(
            self, "1-Ch Rx",
                gr.io_signature(1, 1, gr.sizeof_gr_complex*1),
                gr.io_signature(1, 1, gr.sizeof_char*1),
        )

        ##################################################
        # Variables
        ##################################################
        self.channel_rate = channel_rate = 400000
        self.bit_time = bit_time = 20.0E-6 / 2

        ##################################################
        # Blocks
        ##################################################
        self.digital_clock_recovery_mm_xx_0 = digital.clock_recovery_mm_ff(channel_rate * 20.0E-6 / 2, 0.25*(0.05*0.05), 0.5, 0.05, 0.005)
        self.digital_binary_slicer_fb_0 = digital.binary_slicer_fb()
        self.analog_quadrature_demod_cf_0 = analog.quadrature_demod_cf(-channel_rate/(115000*2*3.1416))


        ##################################################
        # Connections
        ##################################################
        self.connect((self.analog_quadrature_demod_cf_0, 0), (self.digital_clock_recovery_mm_xx_0, 0))
        self.connect((self.digital_binary_slicer_fb_0, 0), (self, 0))
        self.connect((self.digital_clock_recovery_mm_xx_0, 0), (self.digital_binary_slicer_fb_0, 0))
        self.connect((self, 0), (self.analog_quadrature_demod_cf_0, 0))


    def get_channel_rate(self):
        return self.channel_rate

    def set_channel_rate(self, channel_rate):
        self.channel_rate = channel_rate
        self.digital_clock_recovery_mm_xx_0.set_omega(self.channel_rate * 20.0E-6 / 2)
        self.analog_quadrature_demod_cf_0.set_gain(-self.channel_rate/(115000*2*3.1416))

    def get_bit_time(self):
        return self.bit_time

    def set_bit_time(self, bit_time):
        self.bit_time = bit_time

