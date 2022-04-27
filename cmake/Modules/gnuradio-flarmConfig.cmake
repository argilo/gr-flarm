find_package(PkgConfig)

PKG_CHECK_MODULES(PC_GR_FLARM gnuradio-flarm)

FIND_PATH(
    GR_FLARM_INCLUDE_DIRS
    NAMES gnuradio/flarm/api.h
    HINTS $ENV{FLARM_DIR}/include
        ${PC_FLARM_INCLUDEDIR}
    PATHS ${CMAKE_INSTALL_PREFIX}/include
          /usr/local/include
          /usr/include
)

FIND_LIBRARY(
    GR_FLARM_LIBRARIES
    NAMES gnuradio-flarm
    HINTS $ENV{FLARM_DIR}/lib
        ${PC_FLARM_LIBDIR}
    PATHS ${CMAKE_INSTALL_PREFIX}/lib
          ${CMAKE_INSTALL_PREFIX}/lib64
          /usr/local/lib
          /usr/local/lib64
          /usr/lib
          /usr/lib64
          )

include("${CMAKE_CURRENT_LIST_DIR}/gnuradio-flarmTarget.cmake")

INCLUDE(FindPackageHandleStandardArgs)
FIND_PACKAGE_HANDLE_STANDARD_ARGS(GR_FLARM DEFAULT_MSG GR_FLARM_LIBRARIES GR_FLARM_INCLUDE_DIRS)
MARK_AS_ADVANCED(GR_FLARM_LIBRARIES GR_FLARM_INCLUDE_DIRS)
