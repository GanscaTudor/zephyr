/*
 * Copyright (c) 2026 Analog Devices, Inc.
 *
 * SPDX-License-Identifier: Apache-2.0
 *
 * Placeholder "ad74413r" IIO device without channels. pyadi-iio's swiot1l
 * class opens the ad74413r device as soon as the swiot device is in
 * "runtime" mode and raises if it is missing, so it must exist for hosts
 * using that class to connect, even though the AD74413R is not supported
 * yet.
 */

#include <zephyr/device.h>
#include <iio/iio-backend.h>
#include <iio_device.h>

static int iio_ad74413r_add_channels(const struct device *dev, struct iio_device *iio_device)
{
	ARG_UNUSED(dev);
	ARG_UNUSED(iio_device);

	return 0;
}

static DEVICE_API(iio_device, iio_ad74413r_api) = {
	.add_channels = iio_ad74413r_add_channels,
};

DEVICE_DEFINE(iio_ad74413r, "iio_ad74413r", NULL, NULL, NULL, NULL, POST_KERNEL,
	      CONFIG_KERNEL_INIT_PRIORITY_DEVICE, &iio_ad74413r_api);

IIO_DEVICE_INFO_DEFINE(iio_ad74413r_info, DEVICE_GET(iio_ad74413r), "ad74413r");
