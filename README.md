![Logo](https://raw.githubusercontent.com/acarlo79/solar-ev-manager/main/icon.png)

# ☀️ Solar EV Manager for Home Assistant

A high-performance custom integration for Home Assistant designed to route excess solar energy into your Tesla. This integration balances real-time solar production with home battery preservation and Tesla API safety.

⚠️ **Compatibility Notice:** This integration is designed specifically for **Tesla vehicles** using the Tesla Fleet API.

## 🎯 The Goal
This project solves the "Octopus vs. Solar" conflict. It ensures that during the day, your car only charges from free sunshine, but when the sun goes down, it steps aside to allow smart tariffs (like Octopus Intelligent) to manage your cheap overnight charging.

## ✨ Key Features

* **Rolling Data Smoothing (C):** Uses a 2-minute rolling average of your power data. This prevents the car from reacting to "jittery" solar spikes, resulting in a smooth, stable charging curve.
* **API & Contactor Protection (A):** Features a 5-minute (300s) safety buffer. The integration will wait for 5 minutes of consistent low-solar data before pausing the car. This prevents mechanical wear on your car's contactors and protects your Tesla Fleet API rate limits.
* **Smart Amperage Deadband (B):** Only sends a command to change the car's charging speed if the required change is 2 Amps or greater. This eliminates unnecessary "micro-adjustments" and keeps your API usage low.
* **Battery Feedback Protection:** Automatically detects when your house battery is discharging to cover the car's load and throttles the car back to protect your home storage.
* **Live Diagnostic Sensors:** Provides real-time `Excess Watts` and `Target Amps` entities for your dashboard, showing you exactly how the rolling average is calculating your power.

## ⚙️ How It Works

1. **The Calculation:** The engine calculates `(Grid Export * -1) + (EV Load) + (Battery Discharge)`.
2. **The Smoothing:** That value is added to a 120-second history window. The script uses the **average** of that window to determine the next move.
3. **The Buffer:** If the average suggests a change, a 5-minute timer starts. If the solar levels recover before the timer ends, the command is cancelled, and the car's charging session remains uninterrupted.
4. **The Handoff:** When enabled, it turns OFF the Octopus Intelligent Smart Charge switch to take control. When disabled, it turns it back ON to allow overnight scheduling.

## 📋 Required Entities

### 1. Power Sensors
* **Grid Power Sensor:** Must be in **Watts (W)**. Negative (-) for Export, Positive (+) for Import.
* **EV Power Sensor:** Must be in **Watts (W)**. Measures the car's live draw.
* **Live Voltage Sensor:** Must be in **Volts (V)**.
* **House Battery Sensor:** Must be in **Kilowatts (kW)**. Negative (-) for Discharging, Positive (+) for Charging.

### 2. Tesla & Octopus Entities
* **Tesla Charge Switch:** The main toggle to start/stop charging.
* **Tesla Amps Slider:** The `number` entity controlling the charging limit.
* **Tesla Cable Sensor:** Supports `sensor` or `binary_sensor`. The integration only runs when state is `Connected` or `On`.
* **Octopus Intelligent Switch:** The master switch to enable/disable smart charging.

## 🚀 Installation

1. Add this URL as a Custom Repository in **HACS**.
2. Download and **Restart Home Assistant**.
3. Go to **Settings > Devices & Services > Add Integration**.
4. Search for **Solar EV Manager** and follow the UI setup wizard.

## 🕹️ Usage
Turn the **Solar EV Manager Master Switch** ON in the morning. The integration will immediately suspend your Octopus schedule and begin stalking the sun. In the evening, turn it OFF to allow your car to charge at off-peak rates.
