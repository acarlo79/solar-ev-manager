# ☀️ Solar EV Manager for Home Assistant

A custom Home Assistant integration designed to flawlessly route your excess solar energy directly into your car. It dynamically adjusts your charging speed second-by-second to match your roof's production, completely eliminating accidental grid imports while your house appliances take priority. 

⚠️ **Compatibility Notice: This integration is currently ONLY compatible with Tesla vehicles.** It specifically utilizes the Tesla Fleet API's native ability to adjust charging amps dynamically on the fly. 

## 🎯 The Goal
The primary goal of this project is to solve the "Octopus vs. Solar" conflict. 

Many EV owners use smart tariffs (like Octopus Intelligent) for cheap overnight charging, but those smart schedules often fight with daytime solar charging setups. This integration acts as the ultimate referee:
* **During the Day:** It pauses the Octopus schedule and precisely throttles your Tesla's charging amps to perfectly surf your solar export curve.
* **At Night (or when disabled):** It instantly pauses the car and hands control back to Octopus Energy, allowing it to calculate and schedule your cheap overnight top-up.

## ⚙️ How It Works

This integration does not rely on cloud guessing or delayed inverter data. It calculates your exact excess power using live hardware clamps (like a Shelly EM) to ensure your home *always* gets priority.

Here is the logic engine under the hood:
1. **Live Math:** It continuously monitors your Main Grid clamp (Import/Export) and your EV Charger clamp. By calculating `(Grid Export) + (Current EV Load)`, it determines the *True Excess* solar available, even while the car is currently charging.
2. **Voltage Accuracy:** It divides your True Excess Watts by your *Live Grid Voltage* to calculate the exact Amps available, preventing mathematical overdraws caused by voltage fluctuations.
3. **Dynamic Throttling:** It seamlessly slides your Tesla's charging limit up and down between 5A and 32A to perfectly match the sun.
4. **The Cloud Safety Net:** If a cloud rolls over (or someone turns on the oven) and your available solar drops below Tesla's minimum 5A limit, the integration instantly pauses the charge to protect you from pulling grid power, resuming only when the sun comes back out.

## 📋 Prerequisites
To use this integration, your Home Assistant instance must have the following entities available:
* **Grid Power Sensor:** A sensor reading your main mains connection (must read *Negative* for export and *Positive* for import).
* **EV Power Sensor:** A sensor reading the live wattage of your EV charger circuit.
* **Live Voltage Sensor:** A sensor reporting live house voltage. 
* **Tesla Fleet Integration:** A working connection to your Tesla, exposing the `switch.charge` and `number.charge_current` entities.
* **Octopus Energy Integration:** Specifically, the Intelligent Smart Charge switch (`switch.octopus_intelligent...`).

## 🚀 Installation

This integration is fully UI-configurable and requires **zero YAML editing**.

1. Add this repository to [HACS](https://hacs.xyz/) as a Custom Repository (Category: Integration).
2. Download **Solar EV Manager** through HACS.
3. Completely **Restart Home Assistant**.
4. Go to **Settings > Devices & Services**.
5. Click **+ Add Integration** and search for "Solar EV Manager".
6. Follow the UI setup wizard to select your sensors from the dropdown menus.

## 🕹️ Usage
Once installed, the integration will generate a single master switch entity (e.g., `switch.solar_ev_manager`). 

Place this switch on your dashboard:
* **Turn ON:** Octopus is suspended, and the car tracks the sun.
* **Turn OFF:** Solar tracking stops, the car pauses, and Octopus takes over for the night.
