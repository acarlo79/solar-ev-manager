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
1. **Live Math:** It continuously monitors your Main Grid clamp (Import/Export) and your EV Charger clamp. By calculating `(Grid Export * -1) + (Current EV Load)`, it determines the *True Excess* solar available, even while the car is currently charging.
2. **Voltage Accuracy:** It divides your True Excess Watts by your *Live Grid Voltage* to calculate the exact Amps available, preventing mathematical overdraws caused by voltage fluctuations.
3. **Dynamic Throttling:** It seamlessly slides your Tesla's charging limit up and down between 5A and 32A to perfectly match the sun.
4. **The Cloud Safety Net:** If a cloud rolls over (or someone turns on the oven) and your available solar drops below Tesla's minimum 5A limit, the integration instantly pauses the charge to protect you from pulling grid power, resuming only when the sun comes back out.

## 📋 Required Entities & Sensor Details

To use this integration, your Home Assistant instance must have the following entities available. During setup, you will map these entities using the UI wizard.

### 1. Hardware Power Sensors (e.g., Shelly EM, CT Clamps)
* **Grid Power Sensor (`sensor`)**
  * **What it does:** Measures your main grid connection.
  * **Why it's needed:** Acts as the absolute source of truth to guarantee your house appliances get priority over the car. 
  * **Required Format:** Must report in **Watts (W)**. Crucially, it must report **Negative numbers when exporting to the grid** and **Positive numbers when importing**. 
* **EV Power Sensor (`sensor`)**
  * **What it does:** Measures the live power consumption of your EV charger circuit.
  * **Why it's needed:** Because the EV load is hidden *inside* the Grid Power reading, the math needs to extract this number to calculate your "True" total solar availability.
  * **Required Format:** Must report in **Watts (W)**.
* **Live Voltage Sensor (`sensor`)**
  * **What it does:** Reads the live voltage of your house.
  * **Why it's needed:** Amps = Watts ÷ Volts. Voltage fluctuates (usually between 230V and 250V). Using live voltage ensures the Amp calculation is flawless down to the last decimal, preventing accidental grid imports.
  * **Required Format:** Must report in **Volts (V)**. (If this sensor goes offline, the integration safely defaults to 240V).

### 2. Tesla Integration Entities
* **Tesla Charge Switch (`switch`)**
  * **What it does:** Turns charging on and off.
  * **Why it's needed:** Used to pause charging when a cloud rolls over, and to wake the car up when the sun comes back out.
* **Tesla Amps Slider (`number`)**
  * **What it does:** The slider that controls the charging speed.
  * **Why it's needed:** This is what the integration actively manipulates to ride your solar curve.
  * **Required Format:** Standard Home Assistant `number` entity (usually ranges from 5 to 32).
* **Tesla Cable Sensor (`sensor`)**
  * **What it does:** Detects if the charging cable is physically plugged into the car.
  * **Why it's needed:** Prevents the integration from spamming the Tesla API with Amp changes when you are driving or unplugged.
  * **Required Format:** Must report the exact string **`Disconnected`** when the cable is unplugged.

### 3. Octopus Energy Entities
* **Intelligent Smart Charge Switch (`switch`)**
  * **What it does:** The master switch provided by the Octopus Energy integration.
  * **Why it's needed:** The integration turns this `off` to suspend your schedule during the day, and turns it `on` to hand control back to Octopus at night.

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
* **Turn ON (Morning):** Octopus is suspended, and the car tracks the sun.
* **Turn OFF (Evening):** Solar tracking stops, the car pauses, and Octopus takes over to schedule your cheap night charging.
