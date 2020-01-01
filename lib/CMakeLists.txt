# Copyright 2011,2012 Free Software Foundation, Inc.
#
# This file is part of GNU Radio
#
# GNU Radio is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
#
# GNU Radio is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with GNU Radio; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.

########################################################################
# Setup library
########################################################################
include(GrPlatform) #define LIB_SUFFIX

include_directories(${Boost_INCLUDE_DIR})
link_directories(${Boost_LIBRARY_DIRS})

list(APPEND flarm_sources
)

set(flarm_sources "${flarm_sources}" PARENT_SCOPE)
if(NOT flarm_sources)
	MESSAGE(STATUS "No C++ sources... skipping lib/")
	return()
endif(NOT flarm_sources)

add_library(gnuradio-flarm SHARED ${flarm_sources})
target_link_libraries(gnuradio-flarm ${Boost_LIBRARIES} gnuradio::gnuradio-runtime gnuradio::gnuradio-blocks gnuradio::gnuradio-filter gnuradio::gnuradio-blocks gnuradio::gnuradio-fft volk)
target_include_directories(gnuradio-flarm
    PUBLIC $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/../include>
    PUBLIC $<INSTALL_INTERFACE:include>
  )
set_target_properties(gnuradio-flarm PROPERTIES DEFINE_SYMBOL "gnuradio_flarm_EXPORTS")

if(APPLE)
    set_target_properties(gnuradio-flarm PROPERTIES
        INSTALL_NAME_DIR "${CMAKE_INSTALL_PREFIX}/lib"
    )
endif(APPLE)

########################################################################
# Install built library files
########################################################################
install(TARGETS gnuradio-flarm
    LIBRARY DESTINATION lib${LIB_SUFFIX} # .so/.dylib file
    ARCHIVE DESTINATION lib${LIB_SUFFIX} # .lib file
    RUNTIME DESTINATION bin              # .dll file
)

########################################################################
# Build and register unit test
########################################################################
include(GrTest)

include_directories(${CPPUNIT_INCLUDE_DIRS})

list(APPEND test_flarm_sources
    ${CMAKE_CURRENT_SOURCE_DIR}/test_flarm.cc
    ${CMAKE_CURRENT_SOURCE_DIR}/qa_flarm.cc
)

list(APPEND GR_TEST_TARGET_DEPS flarm)

foreach(qa_file ${test_flarm_sources})
    GR_ADD_CPP_TEST("flarm_${qa_file}"
        ${CMAKE_CURRENT_SOURCE_DIR}/${qa_file}
    )
endforeach(qa_file)