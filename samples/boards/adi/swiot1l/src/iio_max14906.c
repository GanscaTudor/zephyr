/*
 * Copyright (c) 2026 Analog Devices, Inc.
 *
 * SPDX-License-Identifier: Apache-2.0
 *
 * "max14906" IIO device: one output channel per MAX14906 channel
 * (voltage0..voltage3), backed by the max14906 GPIO controller. The "raw"
 * attribute sets or reads the channel level, as with the no-OS firmware.
 */

#include <errno.h>
#include <stdlib.h>
#include <string.h>

#include <zephyr/device.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/logging/log.h>
#include <iio/iio-backend.h>
#include <iio_device.h>

LOG_MODULE_REGISTER(iio_max14906, LOG_LEVEL_INF);

#define MAX14906_CHANNELS 4

static const struct device *const max14906 = DEVICE_DT_GET(DT_NODELABEL(max14906));

static int iio_max14906_add_channels(const struct device *dev, struct iio_device *iio_device)
{
	static const char *const attrs[] = { "raw", "scale", "offset" };
	const struct iio_data_format fmt = {
		.length = 8,
		.bits = 1,
	};
	char id[16];

	ARG_UNUSED(dev);

	for (uint32_t ch = 0; ch < MAX14906_CHANNELS; ch++) {
		struct iio_channel *chn;

		snprintk(id, sizeof(id), "voltage%u", ch);

		chn = iio_device_add_channel(iio_device, ch, id, NULL, NULL, true, false, &fmt);
		if (iio_err(chn)) {
			LOG_ERR("Could not add channel %s", id);
			return -EINVAL;
		}

		iio_channel_set_pdata(chn, (struct iio_channel_pdata *)(uintptr_t)ch);

		for (size_t i = 0; i < ARRAY_SIZE(attrs); i++) {
			if (iio_channel_add_attr(chn, attrs[i], IIO_ATTR_TYPE_CHANNEL, NULL)) {
				LOG_ERR("Could not add %s to %s", attrs[i], id);
				return -EINVAL;
			}
		}
	}

	return 0;
}

static gpio_pin_t attr_channel(const struct iio_attr *attr)
{
	return (gpio_pin_t)(uintptr_t)iio_channel_get_pdata(attr->iio.chn);
}

static int iio_max14906_read_attr(const struct device *dev, const struct iio_device *iio_device,
				  const struct iio_attr *attr, char *dst, size_t len)
{
	int val;

	ARG_UNUSED(dev);
	ARG_UNUSED(iio_device);

	if (attr->type != IIO_ATTR_TYPE_CHANNEL) {
		return -EINVAL;
	}

	if (strcmp(attr->name, "raw") == 0) {
		if (!device_is_ready(max14906)) {
			return -ENODEV;
		}
		val = gpio_pin_get(max14906, attr_channel(attr));
		if (val < 0) {
			return val;
		}
		return snprintk(dst, len, "%d", val) + 1;
	} else if (strcmp(attr->name, "scale") == 0) {
		return snprintk(dst, len, "1") + 1;
	} else if (strcmp(attr->name, "offset") == 0) {
		return snprintk(dst, len, "0") + 1;
	}

	return -EINVAL;
}

static int iio_max14906_write_attr(const struct device *dev, const struct iio_device *iio_device,
				   const struct iio_attr *attr, const char *src, size_t len)
{
	int ret;

	ARG_UNUSED(dev);
	ARG_UNUSED(iio_device);

	if (attr->type != IIO_ATTR_TYPE_CHANNEL || strcmp(attr->name, "raw") != 0) {
		return -EINVAL;
	}

	if (!device_is_ready(max14906)) {
		return -ENODEV;
	}

	ret = gpio_pin_set(max14906, attr_channel(attr), strtoul(src, NULL, 10) ? 1 : 0);
	if (ret < 0) {
		return ret;
	}

	return (int)len;
}

static DEVICE_API(iio_device, iio_max14906_api) = {
	.add_channels = iio_max14906_add_channels,
	.read_attr = iio_max14906_read_attr,
	.write_attr = iio_max14906_write_attr,
};

DEVICE_DEFINE(iio_max14906, "iio_max14906", NULL, NULL, NULL, NULL, POST_KERNEL,
	      CONFIG_KERNEL_INIT_PRIORITY_DEVICE, &iio_max14906_api);

IIO_DEVICE_INFO_DEFINE(iio_max14906_info, DEVICE_GET(iio_max14906), "max14906");
