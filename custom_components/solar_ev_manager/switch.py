import logging
import asyncio
import math
from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.const import STATE_ON, STATE_OFF

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([SolarEVManagerSwitch(hass, entry)])

class SolarEVManagerSwitch(SwitchEntity):
    def __init__(self, hass, entry):
        self.hass = hass
        self.entry = entry
        self.conf = entry.data
        self._attr_name = "Solar EV Manager"
        self._attr_unique_id = "solar_ev_manager_master_switch"
        self._attr_icon = "mdi:solar-power"
        self._is_on = False
        self._listener = None
        self._current_amps = None
        self._signal_name = f"solar_ev_update_{entry.entry_id}"

    @property
    def is_on(self):
        return self._is_on

    async def async_turn_on(self, **kwargs):
        self._is_on = True
        self.async_write_ha_state()
        
        await self.hass.services.async_call("switch", "turn_off", {"entity_id": self.conf["octopus_switch"]})
        await asyncio.sleep(5)
        await self.hass.services.async_call("switch", "turn_on", {"entity_id": self.conf["tesla_switch"]})
        
        # LISTENER UPDATE: The battery_sensor is now in this list!
        self._listener = async_track_state_change_event(
            self.hass, 
            [
                self.conf["grid_sensor"], 
                self.conf["ev_sensor"], 
                self.conf["voltage_sensor"], 
                self.conf["tesla_cable"],
                self.conf["battery_sensor"] 
            ], 
            self._calculate_and_adjust
        )
        
        await self._calculate_and_adjust(None)

    async def async_turn_off(self, **kwargs):
        self._is_on = False
        self.async_write_ha_state()
        
        if self._listener:
            self._listener() 
            self._listener = None
            
        async_dispatcher_send(self.hass, self._signal_name, 0.0, 0)
            
        await self.hass.services.async_call("switch", "turn_on", {"entity_id": self.conf["octopus_switch"]})
        await self.hass.services.async_call("switch", "turn_off", {"entity_id": self.conf["tesla_switch"]})

    async def _calculate_and_adjust(self, event):
        if not self._is_on:
            return
            
        cable_state = self.hass.states.get(self.conf["tesla_cable"])
        if cable_state and cable_state.state.lower() == "disconnected":
            _LOGGER.debug("Tesla cable is disconnected. Returning 0.")
            async_dispatcher_send(self.hass, self._signal_name, 0.0, 0)
            return
            
        grid_state = self.hass.states.get(self.conf["grid_sensor"])
        ev_state = self.hass.states.get(self.conf["ev_sensor"])
        volt_state = self.hass.states.get(self.conf["voltage_sensor"])
        batt_state = self.hass.states.get(self.conf["battery_sensor"])
        
        _LOGGER.debug(f"RAW SENSORS -> Grid: {grid_state.state if grid_state else None}, EV: {ev_state.state if ev_state else None}, Volt: {volt_state.state if volt_state else None}, Batt: {batt_state.state if batt_state else None}")
        
        try:
            grid = float(grid_state.state) if grid_state else 0.0
            ev = float(ev_state.state) if ev_state else 0.0
            voltage = float(volt_state.state) if volt_state else 240.0
            battery_kw = float(batt_state.state) if batt_state else 0.0
        except ValueError:
            _LOGGER.error("Float conversion error in sensors!")
            return
            
        battery_w = battery_kw * 1000
        battery_discharge_w = min(0, battery_w)
            
        excess_watts = (grid * -1) + ev + battery_discharge_w 
        
        target_amps = math.floor(excess_watts / voltage)
        clamped_amps = max(0, min(32, target_amps))
        
        _LOGGER.debug(f"MATH -> Batt_W: {battery_w}W | Discharge factor: {battery_discharge_w}W | Excess: {excess_watts}W | Target: {clamped_amps}A")
        
        async_dispatcher_send(self.hass, self._signal_name, excess_watts, clamped_amps)
        
        charge_switch = self.hass.states.get(self.conf["tesla_switch"])
        
        if clamped_amps >= 5:
            if charge_switch and charge_switch.state != STATE_ON:
                _LOGGER.info("Target >= 5A. Waking Tesla.")
                await self.hass.services.async_call("switch", "turn_on", {"entity_id": self.conf["tesla_switch"]})
                
            if self._current_amps != clamped_amps:
                _LOGGER.info(f"Changing Tesla limit to {clamped_amps}A.")
                await self.hass.services.async_call("number", "set_value", {
                    "entity_id": self.conf["tesla_amps"],
                    "value": clamped_amps
                })
                self._current_amps = clamped_amps
        else:
            if charge_switch and charge_switch.state != STATE_OFF:
                _LOGGER.info("Target < 5A. Pausing Tesla.")
                await self.hass.services.async_call("switch", "turn_off", {"entity_id": self.conf["tesla_switch"]})
                self._current_amps = None
