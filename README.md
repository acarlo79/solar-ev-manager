![Logo](https://raw.githubusercontent.com/acarlo79/solar-ev-manager/main/icon.png)

# ☀️ Solar EV Manager for Home Assistant

A custom Home Assistant integration designed to flawlessly route your excess solar energy directly into your car. It dynamically adjusts your charging speed second-by-second to match your roof's production, completely eliminating accidental grid imports while your house appliances take priority. 

⚠️ **Compatibility Notice: This integration is currently ONLY compatible with Tesla vehicles.** It specifically utilizes the Tesla Fleet API's native ability to adjust charging amps dynamically on the fly. 

## 🎯 The Goal
The primary goal of this project is to solve the "Octopus vs. Solar" conflict. 

Many EV owners use smart tariffs (like Octopus Intelligent) for cheap overnight charging, but those smart schedules often fight with daytime solar charging setups. This integration acts as the ultimate referee:
* **During the Day:** It pauses the Octopus schedule and precisely throttles your Tesla's charging amps to perfectly surf your solar export curve.
* **At Night (or when disabled):** It instantly pauses the car and hands control back to Octopus Energy, allowing it to schedule your cheap overnight top-up.

## ✨ Key Features

* **100% UI Configurable:** No YAML required! Fully translated, step-by-step setup wizard right inside Home Assistant.
* **Smart Battery Protection:** Prevents the dreaded "Battery Feedback Loop." It monitors your home battery and automatically subtracts battery discharge from the math, ensuring your car never drains your house battery.
* **Contactor & API Protection (Debouncing):** Features a built-in 10-second stabilization timer. If a cloud rolls over, the script waits 10 seconds to ensure the weather change is permanent before waking/pausing the car, saving your hardware and protecting you from Tesla API rate limits.
* **Live UI Dashboard Sensors:** Includes two live diagnostic sensors (`Excess Watts` and `Target Amps`) that you can place on your dashboard to watch the logic engine perform its math in real-time.
* **Strict Cable Shield:** Actively monitors your charging port (supporting both standard and binary sensors). If the car is unplugged or asleep, it instantly halts all math to protect the API.

## ⚙️ How It Works
This integration does not rely on cloud guessing or delayed inverter data. It calculates your exact excess power using live hardware clamps to ensure your home *always* gets priority.

1. **Live Math:** `(Grid Export * -1) + (Current EV Load) + (Battery Discharge)`. By calculating this every few seconds, it determines the *True Excess* solar available.
2. **Voltage Accuracy:** It divides your True Excess Watts by your *Live Grid Voltage* to calculate the exact Amps available, preventing mathematical overdraws caused by voltage fluctuations.
3. **Dynamic Throttling:** It seamlessly slides your Tesla's charging limit up and down between 5A and 32A to perfectly match the sun.

## 📋 Required Entities & Sensor Details

During setup, you will map the following entities using the UI wizard:

### 1. Hardware Power Sensors
* **Grid Power Sensor (`sensor`)**
  * **Required Format:** Must report in **Watts (W)**. Must report **Negative (-)** numbers when exporting to the grid, and **Positive (+)** when importing. 
* **EV Power Sensor (`sensor`)**
  * **Required Format:** Must report the live consumption of the charger in **Watts (W)**.
* **Live Voltage Sensor (`sensor`)**
  * **Required Format:** Must report live house voltage in **Volts (V)**.
* **House Battery Sensor (`sensor`)**
  * **Required Format:** Must report in **Kilowatts (kW)**. Must report **Negative (-)** numbers when the battery is *Discharging* into the house, and **Positive (+)** when charging.

### 2. Tesla Integration Entities
* **Tesla Charge Switch (`switch`):** Turns charging on and off.
* **Tesla Amps Slider (`number`):** The slider that controls the charging speed (5A - 32A).
* **Tesla Cable Sensor (`sensor` or `binary_sensor`):** Detects if the charging cable is physically plugged into the car. *Note: The integration will only run if this sensor reports exactly `Connected` or `On`.*

### 3. Octopus Energy Entities
* **Intelligent Smart Charge Switch (`switch`):** The master switch provided by the Octopus Energy integration.

## 🚀 Installation

1. Add this repository to [HACS](https://hacs.xyz/) as a Custom Repository (Category: Integration).
2. Download **Solar EV Manager** through HACS.
3. Completely **Restart Home Assistant**.
4. Go to **Settings > Devices & Services**.
5. Click **+ Add Integration**, search for "Solar EV Manager", and follow the UI wizard.

## 🕹️ Usage

Once installed, the integration generates a Master Switch and two Diagnostic Sensors. Group them together on your dashboard!

* **Master Switch ON (Morning):** Octopus is suspended, the sensors wake up, and the car tracks the sun.
* **Master Switch OFF (Evening):** Solar tracking stops, the car pauses, and Octopus takes over to schedule your cheap night charging.
* **Target Amps Sensor:** Watch this to see exactly what charging speed the script is calculating.
* **Excess Watts Sensor:** Watch this to see exactly how much true solar excess is available at your meter.
