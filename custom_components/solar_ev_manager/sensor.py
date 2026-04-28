from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.dispatcher import async_dispatcher_connect

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the debug sensors."""
    async_add_entities([
        SolarEVDebugSensor(hass, entry, "Excess Watts", "excess_watts", "W", "mdi:flash"),
        SolarEVDebugSensor(hass, entry, "Target Amps", "target_amps", "A", "mdi:current-ac")
    ])

class SolarEVDebugSensor(SensorEntity):
    def __init__(self, hass, entry, name, key, unit, icon):
        self.hass = hass
        self.entry = entry
        self._attr_name = f"Solar EV Manager {name}"
        self._attr_unique_id = f"solar_ev_manager_{entry.entry_id}_{key}"
        self._attr_native_unit_of_measurement = unit
        self._attr_icon = icon
        self._key = key
        self._attr_native_value = 0
        self._signal_name = f"solar_ev_update_{entry.entry_id}"

    async def async_added_to_hass(self):
        """Register the sensor to listen for live math updates."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, self._signal_name, self._handle_update
            )
        )

    def _handle_update(self, excess_watts, target_amps):
        """Update the UI when the switch broadcasts new math."""
        if self._key == "excess_watts":
            self._attr_native_value = round(excess_watts, 2)
        elif self._key == "target_amps":
            self._attr_native_value = target_amps
        self.async_write_ha_state()
