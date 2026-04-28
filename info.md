![Logo](https://raw.githubusercontent.com/acarlo79/solar-ev-manager/icon.png)
# Solar EV Manager

A custom Home Assistant integration that automatically manages your EV charging based on excess solar power, cleanly handing off control to Octopus Intelligent when the sun goes down.

## Features
* **100% GUI Configuration:** No YAML required! Set up and map all your sensors directly through the Home Assistant UI.
* **Dynamic Solar Tracking:** Automatically adjusts your Tesla's charging speed (Amps) based on live grid export and voltage data.
* **Octopus Intelligent Handoff:** Seamlessly pauses charging and hands control back to Octopus Energy when solar charging is disabled so your nightly off-peak schedules work perfectly.
* **Master Control Switch:** Creates a single master switch entity to easily toggle solar tracking on and off.

## Installation & Setup

1. Install this integration via HACS and **restart Home Assistant**.
2. Go to **Settings** > **Devices & Services**.
3. Click the **+ Add Integration** button in the bottom right corner.
4. Search for **Solar EV Manager**.
5. Follow the native setup wizard to select your Grid, EV, Voltage, Tesla, and Octopus entities from the simple dropdown menus. 
6. Click Submit, and you are done!
