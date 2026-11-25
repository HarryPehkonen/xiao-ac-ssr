# Driving PlatformIO yourself

A mental model plus the commands that matter, for `firmware/bringupB` and every project after it.
Tool: **PlatformIO Core 6.2.0** (installed here via `uv tool install --python 3.13 platformio`).

## The mental model: one folder, one recipe, one generated directory

    firmware/bringupB/
      platformio.ini     the recipe: platform, board, framework, options   <- the only file you write
      src/main.cpp       your code
      include/           headers (a gitignored secrets.h would go here)
      lib/               project-local libraries (none in this project)
      .pio/              generated: the downloaded toolchain + build output (gitignored, disposable)

`platformio.ini` is the contract, and pinning it is what makes a build reproducible: it fixes *which*
toolchain and framework version this project uses, so the same commit builds the same image on the
laptop and on the MacBook. Nothing lives in global state, so there are no "installed libraries" to
drift between machines. The corollary is worth internalising: to reproduce a build you need the repo
and an internet connection, and nothing else.

Machine-wide storage is `~/.platformio` (packages, toolchains, platform caches). `pio system info`
prints it. Deleting a project's `.pio/` costs one rebuild; deleting `~/.platformio` costs the download.

## The commands that matter

Run these inside `firmware/bringupB/`, or from anywhere with `-d <dir>`.

| command | what it does | when you use it |
| --- | --- | --- |
| `pio run` | compile and link only | "does my code build?" |
| `pio run -t upload` | build, then flash over USB | putting it on the board |
| `pio run -t upload -t monitor` | flash, then open the console | the normal bring-up loop |
| `pio device monitor` | serial console (`-b 115200` overrides the ini) | reading the sketch's output |
| `pio run -t clean` | delete build output, keep the toolchain | after editing the ini |
| `pio pkg list` | the exact versions this project resolved | recording a reproducible set |
| `pio device list` | serial ports with hardware IDs | finding the port |
| `pio boards <text>` | search board IDs (`pio boards seeed_xiao`) | starting a new project |
| `pio system info` | paths, versions, where PlatformIO lives | anything looks wrong |
| `pio run -t compiledb` | writes `compile_commands.json` | editor/LSP completion |
| `pio --help` | the whole command surface | exploring |

**Getting out of the monitor is `Ctrl+C`** — `--exit-char` defaults to 3, which is Ctrl+C.

## Reading the build output

    Compiling .pio/build/seeed_xiao_esp32c3/src/main.cpp.o
    Linking .pio/build/seeed_xiao_esp32c3/firmware.elf
    RAM:   [          ]   4.1% (used 13384 bytes from 327680 bytes)
    Flash: [==        ]  20.2% (used 264120 bytes from 1310720 bytes)
    Building .pio/build/seeed_xiao_esp32c3/firmware.bin
    ========================= [SUCCESS] Took 15.45 seconds ========================

- `firmware.elf` is the linked image; **`firmware.bin` is what is actually written to flash**.
- RAM% and Flash% are the two numbers to watch. On a 4 MB part you usually run out of flash first;
  RAM bites when you allocate large buffers.
- The first build takes minutes because it downloads the toolchain. Later builds take seconds and
  recompile only what changed.
- The environment name in `.pio/build/<env>/` comes from the `[env:...]` section of the ini.

## Flashing: the failures you will actually hit

| symptom | cause | fix |
| --- | --- | --- |
| `Could not open port ... Permission denied` | the udev rule isn't live for this session | `ls -l /dev/ttyACM0`; reload with `sudo udevadm control --reload-rules && sudo udevadm trigger` |
| `Failed to connect to ESP32-C3: Timeout waiting for packet header` | the chip never entered download mode | hold **BOOT**, tap **RESET**, release BOOT, upload again |
| flash succeeds, monitor stays silent | nothing has printed yet, or the wrong speed | tap RESET to see the boot banner; check `monitor_speed` |
| port reported busy | another monitor, or ModemManager, holds it | close the other monitor; PlatformIO's udev rules set `ID_MM_DEVICE_IGNORE` for this board |
| no port at all | charge-only cable, or the board is asleep | swap the cable — the C3 needs a data cable |

## This project's loop

    cd firmware/bringupB
    pio run -t upload -t monitor
    #  1 = hold GATE_DRV high, 0 = hold it low, b = blink, s = status   (BOOT button cycles too)

Then measure across `R3` with the meter: **~1.8–2.1 V** while held on, **~0 V** while held off —
BRINGUP section B, rows B1 and B2.

## The reproducibility habit

The first time a build works, record what built it:

    pio pkg list      # platform espressif32 @ 8.0.0, framework-arduinoespressif32 @ 4.30312.261116, ...

and pin the platform in `platformio.ini` (`platform = espressif32@8.0.0`, as this project now does).
Bump a pinned version deliberately, as its own change — never as a side effect of an unrelated build.
