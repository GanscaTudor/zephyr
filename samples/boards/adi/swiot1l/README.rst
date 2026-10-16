.. zephyr:code-sample:: adi-swiot1l
   :name: AD-SWIOT1L-SL 10BASE-T1L

   Bring up the AD-SWIOT1L-SL 10BASE-T1L interface with a static IPv4 address.

Overview
********

This sample brings up the ADIN1110 10BASE-T1L interface of the AD-SWIOT1L-SL
with the static IPv4 address ``192.168.97.40/16``, the same one used by the
Analog Devices no-OS firmware for this board. The green LED follows the T1L
link state and the network shell is available on the console.

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
