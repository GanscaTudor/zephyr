.. zephyr:code-sample:: adi-swiot1l
   :name: AD-SWIOT1L-SL 10BASE-T1L

   Bring up the AD-SWIOT1L-SL 10BASE-T1L interface with a static IPv4 address.

Overview
********

This sample brings up the ADIN1110 10BASE-T1L interface of the AD-SWIOT1L-SL
with the static IPv4 address ``192.168.97.40/16``, the same one used by the
Analog Devices no-OS firmware for this board. The green LED follows the T1L
link state and the network shell is available on the console.

The MAX14906 digital outputs can be driven from the GPIO shell, and optionally
over the network through an IIOD server, with the same ``swiot`` and
``max14906`` IIO devices as the no-OS firmware.

Requirements
************

- AD-SWIOT1L-SL board, powered from its 24 V terminal block.
- A 10BASE-T1L link partner, for example a USB to 10BASE-T1L media converter,
  configured with an address in ``192.168.0.0/16``.

Building and Running
********************

.. zephyr-app-commands::
   :zephyr-app: samples/boards/adi/swiot1l
   :board: ad_swiot1l_sl
   :goals: build flash
   :compact:

Sample Output
=============

.. code-block:: console

   <inf> phy_adin: PHY 1 ID 283BC91
   *** Booting Zephyr OS build v4.5.0 ***
   <inf> net_config: IPv4 address: 192.168.97.40
   <inf> swiot1l: IPv4 192.168.97.40/255.255.0.0
   <inf> swiot1l: T1L link up

The board then answers ping from the link partner, and ``net iface``,
``net ping`` and ``net arp`` can be used from the shell.

To drive a load wired to MAX14906 channel 1 (DOI1), configure the first pin
of the ``max14906`` GPIO controller as an output and set it:

.. code-block:: console

   uart:~$ gpio conf max14906 0 o
   uart:~$ gpio set max14906 0 1
   uart:~$ gpio set max14906 0 0

IIOD server
===========

``overlay-iiod.conf`` adds a libiio IIOD server on TCP port 30431, so the board
can be used from libiio and pyadi-iio hosts with the ``ip:192.168.97.40`` URI.
It needs the libiio module, added to the workspace by ``submanifests/libiio.yaml``
(run ``west update`` first).

.. zephyr-app-commands::
   :zephyr-app: samples/boards/adi/swiot1l
   :board: ad_swiot1l_sl
   :gen-args: -DEXTRA_CONF_FILE=overlay-iiod.conf
   :goals: build flash
   :compact:

The context has three devices:

- ``swiot``: channel configuration (``mode``, ``chN_device``,
  ``chN_function``, ``chN_enable``). A channel assigned to the ``max14906``
  with the ``output`` or ``input`` function is configured on the MAX14906
  when it is enabled.
- ``max14906``: output channels ``voltage0`` to ``voltage3``, whose ``raw``
  attribute sets or reads the channel level.
- ``ad74413r``: placeholder without channels, the AD74413R is not supported
  yet.

For example, to switch MAX14906 channel 1 on and off from a host:

.. code-block:: console

   iio_attr -u ip:192.168.97.40 -d swiot mode config
   iio_attr -u ip:192.168.97.40 -d swiot ch0_device max14906
   iio_attr -u ip:192.168.97.40 -d swiot ch0_function output
   iio_attr -u ip:192.168.97.40 -d swiot ch0_enable 1
   iio_attr -u ip:192.168.97.40 -d swiot mode runtime
   iio_attr -u ip:192.168.97.40 -c max14906 voltage0 raw 1
   iio_attr -u ip:192.168.97.40 -c max14906 voltage0 raw 0
