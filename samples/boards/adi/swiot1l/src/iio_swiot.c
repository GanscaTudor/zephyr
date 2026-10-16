/*
 * Copyright (c) 2026 Analog Devices, Inc.
 *
 * SPDX-License-Identifier: Apache-2.0
 *
 * "swiot" IIO device: the channel configuration device of the no-OS
 * firmware for this board. It has no channels, only the device attributes
 * pyadi-iio's swiot1l class uses (mode, chN_device, chN_function,
 * chN_enable and their _available lists).
 *
 * A channel assigned to the max14906 with the "output" or "input" function
 * is configured on the MAX14906 as soon as it is enabled. Channels assigned
 * to the ad74413r, and the "high_z" function, are only stored: the AD74413R
 * is not supported yet and the MAX14906 GPIO driver has no high-Z mode.
 */

#include <errno.h>
#include <string.h>

#include <zephyr/device.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/logging/log.h>
#include <iio/iio-backend.h>
#include <iio_device.h>

LOG_MODULE_REGISTER(iio_swiot, LOG_LEVEL_INF);

#define SWIOT_CHANNELS 4
#define SWIOT_STR_LEN  16

struct swiot_channel {
	char device[SWIOT_STR_LEN];
	char function[SWIOT_STR_LEN];
	char enable[2];
};

static struct {
	char mode[SWIOT_STR_LEN];
	char identify[2];
	struct swiot_channel ch[SWIOT_CHANNELS];
} swiot = {
	.mode = "config",
	.identify = "0",
};

static const struct device *const max14906 = DEVICE_DT_GET(DT_NODELABEL(max14906));

static const char *const channel_attrs[] = {
	"function", "device", "enable", "function_available", "device_available",
};

static void swiot_apply_channel(uint32_t ch)
{
	const struct swiot_channel *c = &swiot.ch[ch];
	gpio_flags_t flags;
	int ret;

	if (strcmp(c->device, "max14906") != 0 || strcmp(c->enable, "1") != 0) {
		return;
	}

	if (!device_is_ready(max14906)) {
		LOG_ERR("max14906 not ready, channel %u not configured", ch);
		return;
	}

	if (strcmp(c->function, "output") == 0) {
		flags = GPIO_OUTPUT_INACTIVE;
	} else if (strcmp(c->function, "input") == 0) {
		flags = GPIO_INPUT;
	} else {
		return;
	}

	ret = gpio_pin_configure(max14906, ch, flags);
	if (ret < 0) {
		LOG_ERR("Failed to configure max14906 channel %u: %d", ch, ret);
	}
}

static int swiot_add_channels(const struct device *dev, struct iio_device *iio_device)
{
	static const char *const dev_attrs[] = {
		"mode", "mode_available", "identify", "serial_id", "ext_psu",
	};
	char name[32];

	ARG_UNUSED(dev);

	for (size_t i = 0; i < ARRAY_SIZE(dev_attrs); i++) {
		if (iio_device_add_attr(iio_device, dev_attrs[i], IIO_ATTR_TYPE_DEVICE)) {
			return -EINVAL;
		}
	}

	for (uint32_t ch = 0; ch < SWIOT_CHANNELS; ch++) {
		for (size_t i = 0; i < ARRAY_SIZE(channel_attrs); i++) {
			snprintk(name, sizeof(name), "ch%u_%s", ch, channel_attrs[i]);
			if (iio_device_add_attr(iio_device, name, IIO_ATTR_TYPE_DEVICE)) {
				return -EINVAL;
			}
		}
	}

	return 0;
}

/* "chN_<suffix>": return N and point suffix past the underscore, or -1. */
static int parse_channel_attr(const char *name, const char **suffix)
{
	if (strncmp(name, "ch", 2) != 0 || name[2] < '0' || name[2] >= '0' + SWIOT_CHANNELS ||
	    name[3] != '_') {
		return -1;
	}

	*suffix = &name[4];
	return name[2] - '0';
}

static int swiot_read_attr(const struct device *dev, const struct iio_device *iio_device,
			   const struct iio_attr *attr, char *dst, size_t len)
{
	const char *val = NULL;
	const char *suffix;
	int ch;

	ARG_UNUSED(dev);
	ARG_UNUSED(iio_device);

	if (strcmp(attr->name, "mode") == 0) {
		val = swiot.mode;
	} else if (strcmp(attr->name, "mode_available") == 0) {
		val = "config runtime";
	} else if (strcmp(attr->name, "identify") == 0) {
		val = swiot.identify;
	} else if (strcmp(attr->name, "serial_id") == 0) {
		val = "ad-swiot1l-sl";
	} else if (strcmp(attr->name, "ext_psu") == 0) {
		val = "0";
	} else {
		ch = parse_channel_attr(attr->name, &suffix);
		if (ch < 0) {
			return -EINVAL;
		}

		if (strcmp(suffix, "function") == 0) {
			val = swiot.ch[ch].function;
		} else if (strcmp(suffix, "device") == 0) {
			val = swiot.ch[ch].device;
		} else if (strcmp(suffix, "enable") == 0) {
			val = swiot.ch[ch].enable;
		} else if (strcmp(suffix, "function_available") == 0) {
			val = "high_z output input";
		} else if (strcmp(suffix, "device_available") == 0) {
			val = "ad74413r max14906";
		}
	}

	if (val == NULL) {
		return -EINVAL;
	}

	return snprintk(dst, len, "%s", val) + 1;
}

static int swiot_write_attr(const struct device *dev, const struct iio_device *iio_device,
			    const struct iio_attr *attr, const char *src, size_t len)
{
	const char *suffix;
	char *dst;
	size_t size;
	int ch = -1;

	ARG_UNUSED(dev);
	ARG_UNUSED(iio_device);

	if (strcmp(attr->name, "mode") == 0) {
		dst = swiot.mode;
		size = sizeof(swiot.mode);
	} else if (strcmp(attr->name, "identify") == 0) {
		dst = swiot.identify;
		size = sizeof(swiot.identify);
	} else {
		ch = parse_channel_attr(attr->name, &suffix);
		if (ch < 0) {
			return -EINVAL;
		}

		if (strcmp(suffix, "function") == 0) {
			dst = swiot.ch[ch].function;
			size = sizeof(swiot.ch[ch].function);
		} else if (strcmp(suffix, "device") == 0) {
			dst = swiot.ch[ch].device;
			size = sizeof(swiot.ch[ch].device);
		} else if (strcmp(suffix, "enable") == 0) {
			dst = swiot.ch[ch].enable;
			size = sizeof(swiot.ch[ch].enable);
		} else {
			return -EINVAL;
		}
	}

	strncpy(dst, src, size - 1);
	dst[size - 1] = '\0';

	if (ch >= 0) {
		swiot_apply_channel(ch);
	}

	return (int)len;
}

static DEVICE_API(iio_device, swiot_api) = {
	.add_channels = swiot_add_channels,
	.read_attr = swiot_read_attr,
	.write_attr = swiot_write_attr,
};

DEVICE_DEFINE(iio_swiot, "iio_swiot", NULL, NULL, NULL, NULL, POST_KERNEL,
	      CONFIG_KERNEL_INIT_PRIORITY_DEVICE, &swiot_api);

IIO_DEVICE_INFO_DEFINE(iio_swiot_info, DEVICE_GET(iio_swiot), "swiot");
