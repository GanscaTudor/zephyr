# AD-SWIOT1L-SL Zephyr firmware

This branch (`swiot1l/integration`) holds everything needed to build a Zephyr
firmware for the AD-SWIOT1L-SL that replaces the Analog Devices no-OS
`swiot1l` firmware on the network side:

- 10BASE-T1L networking on the ADIN1110, static IPv4 `192.168.97.40/16`
  (same address and MAC as the no-OS firmware).
- MAX14906 quad industrial digital I/O.
- An IIOD server (libiio) with the `swiot`, `max14906` and `ad74413r` IIO
  devices, so hosts written for the no-OS firmware (pyadi-iio,
  `RPI_T1LPSE/main_app.py`) can switch the MAX14906 channels, e.g. the fan.

The application is the `samples/boards/adi/swiot1l` sample. Its
[README](samples/boards/adi/swiot1l/README.rst) describes the IIO devices in
detail.

## Contents

1. [What you need](#1-what-you-need)
2. [Create the workspace](#2-create-the-workspace)
3. [Build](#3-build)
4. [Flash](#4-flash)
5. [Check that it works](#5-check-that-it-works)
6. [Use it from the Raspberry Pi](#6-use-it-from-the-raspberry-pi)
7. [Troubleshooting](#7-troubleshooting)
8. [What is on this branch](#8-what-is-on-this-branch)

## 1. What you need

Hardware:

- AD-SWIOT1L-SL, powered from its 24 V terminal block.
- A MAX32625PICO (DAPLink) connected to the SWD header J3, for flashing and
  for the serial console.
- A 10BASE-T1L link partner: the Raspberry Pi T1L setup, or a USB to
  10BASE-T1L media converter on a PC.

Software:

- Git and Python 3.10 or newer.
- The [Zephyr SDK](https://docs.zephyrproject.org/latest/develop/toolchains/zephyr_sdk.html),
  at least the `arm-zephyr-eabi` toolchain (installed in step 2 if missing).
- Windows: [CMake](https://cmake.org/download/), [Ninja](https://ninja-build.org/),
  `dtc` and `gperf`, for example with
  `winget install Kitware.CMake Ninja-build.Ninja oss-winget.dtc oss-winget.gperf`.
  Linux: follow the Zephyr
  [Getting Started Guide](https://docs.zephyrproject.org/latest/develop/getting_started/index.html)
  for the host packages.

> **Windows:** create the workspace on a short local path **without spaces**
> and **outside OneDrive**, for example `C:\swiot1l`. The devicetree build
> step breaks on paths with spaces, and OneDrive locks files inside `.git`.

## 2. Create the workspace

The workspace only fetches the modules this board needs: `hal_adi`, CMSIS and
`libiio` (the libiio module comes from `submanifests/libiio.yaml`).

Windows (PowerShell):

```powershell
mkdir C:\swiot1l
cd C:\swiot1l

python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install west

west init -m https://github.com/GanscaTudor/zephyr --mr swiot1l/integration -o=--depth=1 .
west config manifest.project-filter -- "-.*,+hal_adi,+cmsis_6,+cmsis,+libiio"
west update --narrow -o=--depth=1
pip install -r zephyr\scripts\requirements-base.txt
```

Linux (bash):

```bash
mkdir ~/swiot1l && cd ~/swiot1l

python3 -m venv .venv
source .venv/bin/activate
pip install west

west init -m https://github.com/GanscaTudor/zephyr --mr swiot1l/integration -o=--depth=1 .
west config manifest.project-filter -- "-.*,+hal_adi,+cmsis_6,+cmsis,+libiio"
west update --narrow -o=--depth=1
pip install -r zephyr/scripts/requirements-base.txt
```

If the Zephyr SDK is not installed yet, install only the Arm toolchain:

```
west sdk install -t arm-zephyr-eabi
```

The workspace then looks like this:

```
swiot1l/
├── .venv/
├── .west/
├── modules/
│   ├── hal/adi, hal/cmsis, hal/cmsis_6
│   └── lib/libiio
└── zephyr/          <- this repository, on swiot1l/integration
```

Every new terminal needs the virtual environment again
(`.\.venv\Scripts\Activate.ps1` or `source .venv/bin/activate`), run from the
workspace directory.

## 3. Build

From the workspace directory:

```
west build -p -b ad_swiot1l_sl zephyr/samples/boards/adi/swiot1l -- "-DEXTRA_CONF_FILE=overlay-iiod.conf"
```

`overlay-iiod.conf` adds the IIOD server; it is what the Raspberry Pi
application needs. Without it you get the network and MAX14906 shell only.

The build ends with a memory report similar to:

```
Memory region         Used Size  Region Size  %age Used
           FLASH:      222944 B         3 MB      7.09%
             RAM:      111640 B       256 KB     42.59%
```

The firmware is `build/zephyr/zephyr.hex`.

## 4. Flash

1. Connect the DAPLink to the PC. It shows up as a USB drive called
   **DAPLINK** and as a serial port.
2. Copy `build/zephyr/zephyr.hex` onto the DAPLINK drive.
3. The drive disappears and comes back when programming is done. If a
   `FAIL.TXT` file appears on it, programming failed; read it and copy again.
4. The board restarts on its own. Otherwise press reset or power cycle it.

## 5. Check that it works

### Serial console

Open the DAPLink serial port (`COMx` on Windows, `/dev/ttyACM0` on Linux) at
**115200 8N1**. After a reset you should see:

```
<inf> phy_adin: PHY 1 ID 283BC91
<inf> phy_adin: PHY 1 2.4V mode supported
*** Booting Zephyr OS build ... ***
<inf> net_config: IPv4 address: 192.168.97.40
<inf> swiot1l: IPv4 192.168.97.40/255.255.0.0
<inf> swiot1l: T1L link up
```

No `<err>` lines should be printed, and the green LED turns on with the
link. Useful shell commands:

| Command | What it shows |
|---|---|
| `net iface` | interface state, MAC `00:18:80:03:25:60`, IPv4 address |
| `net ping 192.168.97.1` | ping from the board to the host |
| `net arp` | the hosts the board has talked to |
| `gpio conf max14906 0 o` then `gpio set max14906 0 1` / `0` | switch MAX14906 channel 1 (DOI1) |

### Network

The host on the T1L link needs an address in `192.168.0.0/16`, for example
`192.168.97.1/16`:

- Linux: `sudo ip addr add 192.168.97.1/16 dev <t1l-interface>`
- Windows (administrator PowerShell):
  `New-NetIPAddress -InterfaceAlias "<adapter name>" -IPAddress 192.168.97.1 -PrefixLength 16`

Then:

```
ping 192.168.97.40
```

### IIO

> **The host needs libiio 1.0.** The IIOD server of this firmware only speaks
> the libiio 1.0 protocol. libiio 0.x clients (for example the 0.26
> `iio_info.exe` that older installers put in `C:\Windows\System32`, or the
> `libiio0` Debian/Raspberry Pi OS package) fail with
> `Unable to create IIO context ip:192.168.97.40: Broken pipe (32)`, even
> though ping works.
>
> - Windows: download `Windows.zip` from the
>   [libiio v1.0.0 release](https://github.com/analogdevicesinc/libiio/releases/tag/v1.0.0)
>   and run the tools from `Windows-VS-2022-x64\Release`, or install
>   `libiio-1.0.0...-setup.exe` from the same release.
> - Linux / Raspberry Pi: build libiio 1.0, see
>   [section 6](#6-use-it-from-the-raspberry-pi).
>
> `iio_info -V` must report `Libiio version: 1.0`.

With the libiio 1.0 command line tools on the host:

```
iio_info -u ip:192.168.97.40
```

lists three devices: `ad74413r` (no channels), `max14906` (4 output channels
`voltage0` to `voltage3`) and `swiot` (25 attributes). To switch channel 1 on
and off, exactly like `main_app.py` does:

```
iio_attr -u ip:192.168.97.40 -d swiot mode config
iio_attr -u ip:192.168.97.40 -d swiot ch0_device max14906
iio_attr -u ip:192.168.97.40 -d swiot ch0_function output
iio_attr -u ip:192.168.97.40 -d swiot ch0_enable 1
iio_attr -u ip:192.168.97.40 -d swiot mode runtime
iio_attr -u ip:192.168.97.40 -c max14906 voltage0 raw 1
iio_attr -u ip:192.168.97.40 -c max14906 voltage0 raw 0
```

`samples/boards/adi/swiot1l/scripts` has two host scripts that do the same as
the fan panel of `main_app.py`. They need the libiio 1.0 library and
`pip install pylibiio` (version 1.0):

- `swiot1l_fan_panel.py`: command line, asks for a duty cycle.
- `swiot1l_app.py`: Tkinter window with a ping status and the fan control.

```
python swiot1l_app.py --ip 192.168.97.40
```

## 6. Use it from the Raspberry Pi

The board keeps the IP address, the MAC address and the IIO device names of
the no-OS firmware, so `main_app.py` itself does not change. Two things on the
Pi may have to:

1. **libiio 1.0.** If the Pi has the `libiio0` package (libiio 0.x), build and
   install libiio 1.0:

   ```bash
   sudo apt install -y build-essential cmake git libxml2-dev libzstd-dev
   git clone --depth 1 --branch v1.0.0 https://github.com/analogdevicesinc/libiio.git
   cd libiio && mkdir build && cd build
   cmake -DWITH_USB_BACKEND=OFF -DHAVE_DNS_SD=OFF ..
   make -j"$(nproc)"
   sudo make install
   sudo ldconfig
   iio_info -V                  # must report Libiio version: 1.0
   iio_info -u ip:192.168.97.40
   ```

2. **pyadi-iio with the `adi.swiot` class.** `main_app.py` uses `adi.swiot`
   and `adi.max14906`. `adi.swiot` is on the `swiot_tw` branch of pyadi-iio
   (the `release/ad-swiot1l-sl` branch renamed it to `adi.swiot1l`, which
   `main_app.py` does not use):

   ```bash
   pip install git+https://github.com/analogdevicesinc/pyadi-iio.git@swiot_tw
   ```

   This also installs `pylibiio` 1.0, the Python bindings for libiio 1.0.

Then:

1. The Pi T1L interface keeps its `192.168.97.x/16` address.
2. `ping 192.168.97.40` must answer, and `iio_info -u ip:192.168.97.40` must
   list `ad74413r`, `max14906` and `swiot`.
3. Start `main_app.py`, press **Connect** on the SWIOT1L panel, set a duty
   cycle and press **Set**.

The exact connect and PWM sequence of the `main_app.py` SWIOT1L panel was
tested against this firmware with pyadi-iio `swiot_tw`, pylibiio 1.0 and
libiio 1.0 on a Windows host. The Raspberry Pi build of libiio above was not
tested.

Only the fan path is backed by hardware: the `ad74413r` device has no
channels yet, so panels that read the AD74413R get no data.

## 7. Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `Activate.ps1 cannot be loaded because running scripts is disabled` | Allow local scripts once: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`. |
| `failed to preprocess devicetree files`, or a path cut at a space | The workspace path has spaces. Move it, see step 1. |
| `west init` / `west update` fails with access denied on `.git` files | The workspace is inside OneDrive. Move it. |
| `File not found: .../overlay-iiod` | PowerShell split the argument. Keep the quotes around `"-DEXTRA_CONF_FILE=overlay-iiod.conf"`. |
| DAPLINK drive missing, or shown as "No Media" | Unplug and replug the DAPLink USB cable. |
| Serial port "access denied" | Another terminal has the port open. Close it. |
| Console works but ping fails and `net iface` says `oper=UP` | Check the T1L cable. With a USB to T1L converter, unplug and replug it: it can stop transmitting after a link loss. |
| `eth_adin2111: Failed to communicate over SPI` | The ADIN1110 straps were not latched. Power cycle the board. |
| `gpio_max14906: ... error detected` and `max14906` not ready | The MAX14906 driver fix of this branch is missing; check that you are on `swiot1l/integration`. |
| `Unable to create IIO context ...: Broken pipe (32)` while ping works | The host libiio is 0.x. Use libiio 1.0, see [IIO](#iio). |
| `iio_info` cannot connect at all | The firmware was built without `overlay-iiod.conf`, or TCP port 30431 is blocked. |
| `module 'adi' has no attribute 'swiot'` | pyadi-iio from the wrong branch. Install the `swiot_tw` branch, see section 6. |
| `libiio version 1.x required` from pylibiio | An old `libiio.so` (0.x) is found first. Remove the `libiio0`/`libiio-dev` packages or run `sudo ldconfig` after installing libiio 1.0. |

## 8. What is on this branch

The branch is based on `analogdevicesinc/zephyr` `main`. Each step is also on
its own branch, stacked in this order:

| Branch | Adds |
|---|---|
| `swiot1l/adin1110` | ADIN1110 board support, `samples/boards/adi/swiot1l` with static IPv4 |
| `swiot1l/max14906` | `gpio_max14906` power-up fault fix, MAX14906 board support, GPIO shell |
| `swiot1l/iiod` | libiio submanifest, optional IIOD server with the `swiot`, `max14906` and `ad74413r` devices |
| `swiot1l/integration` | this guide and the host scripts |

Known limitations:

- AD74413R and ADT75 are not supported yet.
- The MAX14906 GPIO driver has no high-Z mode; `high_z` is only stored.
- The MAX32650 TRNG driver does not build yet, so the firmware uses the
  timer based random generator, which is not cryptographically secure.
