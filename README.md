gr-flarm
========

Author: Clayton Smith  
Email: <argilo@gmail.com>

The goal of this project is to implement a receiver for FLARM signals.
Version 6 of the protocol is implemented.

Build instructions:

    mkdir build
    cd build
    cmake ../
    make
    sudo make install

If your GNU Radio is installed in `/usr` (rather than `/usr/local`), then
replace the third line above with:

    cmake -DCMAKE_INSTALL_PREFIX=/usr ../

After following the build instructions, be sure to restart GNU Radio
Companion so that the new block will be available there.

Any help you can offer with reverse engineering or coding would be
greatly appreciated!
