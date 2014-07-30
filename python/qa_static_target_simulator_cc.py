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

from gnuradio import gr, gr_unittest
from gnuradio import blocks, analog
import radar_swig as radar
import numpy as np
import numpy.fft

class qa_static_target_simulator_cc (gr_unittest.TestCase):

	def setUp (self):
		self.tb = gr.top_block ()

	def tearDown (self):
		self.tb = None

	def test_001_t (self):
		# set up fg
		test_len = 1000
		
		packet_len = test_len
		samp_rate = 2000
		frequency = (0,)
		amplitude = 1
		
		Range = (10,)
		velocity = (15,)
		rcs = (1e9,)
		azimuth = (0,)
		position_rx = (0,)
		center_freq = 1e9
		rndm_phase = True
		self_coupling = False
		self_coupling_db = -10;
		
		src = radar.signal_generator_cw_c(packet_len,samp_rate,frequency,amplitude)
		head = blocks.head(8,test_len)
		sim = radar.static_target_simulator_cc(Range, velocity, rcs, azimuth, position_rx, samp_rate, center_freq, self_coupling_db, rndm_phase, self_coupling)
		mult = blocks.multiply_cc()
		snk = blocks.vector_sink_c()
		
		self.tb.connect(src,head,sim)
		self.tb.connect((sim,0),(mult,0))
		self.tb.connect((head,0),(mult,1))
		self.tb.connect(mult,snk)
		self.tb.run ()
		
		# check data
		data = snk.data()
		doppler_freq = 2*velocity[0]*center_freq/3e8 # peak estimation, calc with doppler formula
		fft = numpy.fft.fft(data) # get fft
		num = np.argmax(abs(fft)) # index of max sample
		fft_freq = samp_rate*num/len(fft) # calc freq out of max sample index, works only for frequencies < samp_rate/2!
		
		self.assertAlmostEqual(fft_freq,doppler_freq,2) # check if peak in data is doppler peak
		
		
	def test_002_t (self):
		# set up fg
		test_len = 1000
		packet_len = 1000
		c_light = 3e8
		
		samp_rate = 1000
		freq = 5
		ampl = 1
		
		R = c_light/2/samp_rate # shift of 1 sample
		rcs = 1e12
		Range = (R,)
		velocity = (0,) # no freq shift
		rcs = (rcs,)
		azimuth = (0,)
		position_rx = (0,)
		center_freq = 1e9
		rndm_phase = False
		self_coupling = False
		self_coupling_db = 1;
		
		src = analog.sig_source_c(samp_rate, analog.GR_COS_WAVE, freq, ampl)
		head = blocks.head(8,test_len)
		s2ts = blocks.stream_to_tagged_stream(8,1,packet_len,"packet_len")
		sim = radar.static_target_simulator_cc(Range, velocity, rcs, azimuth, position_rx, samp_rate, center_freq, self_coupling_db, rndm_phase, self_coupling)
		snk0 = blocks.vector_sink_c()
		snk1 = blocks.vector_sink_c()
		
		self.tb.connect(src,head,s2ts,sim,snk0)
		self.tb.connect(head,snk1)
		self.tb.run()
		
		# check data with shifting of 1 sample
		data_in = snk1.data()
		data_out = snk0.data()
		data_out = data_out/max(np.real(data_out)) # rescale output data
		self.assertComplexTuplesAlmostEqual(data_out[1:len(data_out)-1],data_in[0:len(data_in)-2],4)
		
	def test_003_t (self):
		print "TEST3: DONT WORK (AZIMUTH ESTIMATION)"
		# set up fg
		test_len = 2**12
		
		packet_len = test_len
		samp_rate = 32000
		frequency = (0,)
		amplitude = 1
		
		Range = (30,)
		velocity = (60,)
		rcs = (1e9,)
		azimuth = (5,)
		position_rx = (1,-1)
		center_freq = 2.4e9
		rndm_phase = False
		self_coupling = False
		self_coupling_db = -10;
		
		src = radar.signal_generator_cw_c(packet_len,samp_rate,frequency,amplitude)
		head = blocks.head(8,test_len)
		sim = radar.static_target_simulator_cc(Range, velocity, rcs, azimuth, position_rx, samp_rate, center_freq, self_coupling_db, rndm_phase, self_coupling)
		mult1 = blocks.multiply_conjugate_cc()
		mult2 = blocks.multiply_conjugate_cc()
		snk1 = blocks.vector_sink_c()
		snk2 = blocks.vector_sink_c()
		
		self.tb.connect(src,head,sim)
		self.tb.connect((sim,0),(mult1,0))
		self.tb.connect((head,0),(mult1,1))
		self.tb.connect((sim,1),(mult2,0))
		self.tb.connect((head,0),(mult2,1))
		self.tb.connect(mult1,snk1)
		self.tb.connect(mult2,snk2)
		self.tb.run ()
		
		# check data
		data1 = snk1.data()
		fft1 = numpy.fft.fft(data1) # get fft1
		num1 = np.argmax(abs(fft1)) # index of max sample (data1)
		data2 = snk2.data()
		fft2 = numpy.fft.fft(data2) # get fft2
		num2 = np.argmax(abs(fft2)) # index of max sample (data2)
		print "PHIS:", np.angle(fft1[num1])/2.0/np.pi/center_freq, np.angle(fft2[num2])/2.0/np.pi/center_freq
		delta_phi = np.angle(fft1[num1])/2.0/np.pi/center_freq - np.angle(fft2[num2])/2.0/np.pi/center_freq
		print "DELTA_PHI:", delta_phi
		print "DELTA_R:", 1/2.0/np.pi*3e8/center_freq*delta_phi
		

if __name__ == '__main__':
	gr_unittest.run(qa_static_target_simulator_cc)#, "qa_static_target_simulator_cc.xml")
