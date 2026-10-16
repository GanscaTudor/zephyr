# SPDX-License-Identifier: Apache-2.0

cmake_minimum_required(VERSION 3.20.0)
find_package(Zephyr REQUIRED HINTS $ENV{ZEPHYR_BASE})
project(swiot1l)

target_sources(app PRIVATE src/main.c)
target_sources_ifdef(CONFIG_LIBIIO app PRIVATE
  src/iio_ad74413r.c
  src/iio_max14906.c
  src/iio_swiot.c
)
