INCLUDE(FindPkgConfig)
PKG_CHECK_MODULES(PC_FLARM flarm)

FIND_PATH(
    FLARM_INCLUDE_DIRS
    NAMES flarm/api.h
    HINTS $ENV{FLARM_DIR}/include
        ${PC_FLARM_INCLUDEDIR}
    PATHS ${CMAKE_INSTALL_PREFIX}/include
          /usr/local/include
          /usr/include
)

FIND_LIBRARY(
    FLARM_LIBRARIES
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

include("${CMAKE_CURRENT_LIST_DIR}/flarmTarget.cmake")

INCLUDE(FindPackageHandleStandardArgs)
FIND_PACKAGE_HANDLE_STANDARD_ARGS(FLARM DEFAULT_MSG FLARM_LIBRARIES FLARM_INCLUDE_DIRS)
MARK_AS_ADVANCED(FLARM_LIBRARIES FLARM_INCLUDE_DIRS)
