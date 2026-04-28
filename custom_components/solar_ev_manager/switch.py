import logging
import asyncio
import math
import time
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
        
        # Debounce & Smoothing Variables
        self._current_amps = None
        self._pending_amps = None
        self._adjust_task = None
        self._excess_history = [] 
        self._history_window = 120 # Rolling average over the last 2 minutes
        
        self._signal_name = f"solar_ev_update_{entry.entry_id}"

    @property
    def is_on(self):
        return self._is_on

    async def async_turn_on(self, **kwargs):
        self._is_on = True
        self._excess_history.clear() # Start with a clean slate
        self.async_write_ha_state()
        
        await self.hass.services.async_call("switch", "turn_off", {"entity_id": self.conf["octopus_switch"]})
        await asyncio.sleep(5)
        await self.hass.services.async_call("switch", "turn_on", {"entity_id": self.conf["tesla_switch"]})
        
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
            
        if self._adjust_task:
            self._adjust_task.cancel()
            self._adjust_task = None
        self._pending_amps = None
        self._excess_history.clear()
            
        async_dispatcher_send(self.hass, self._signal_name, 0.0, 0)
            
        await self.hass.services.async_call("switch", "turn_on", {"entity_id": self.conf["octopus_switch"]})
        await self.hass.services.async_call("switch", "turn_off", {"entity_id": self.conf["tesla_switch"]})

    async def _calculate_and_adjust(self, event):
        if not self._is_on:
            return
            
        # 1. STRICT CABLE SHIELD
        cable_state = self.hass.states.get(self.conf["tesla_cable"])
        if cable_state and cable_state.state.lower() not in ["on", "connected"]:
            if self._adjust_task:
                self._adjust_task.cancel()
                self._adjust_task = None
                self._pending_amps = None
            self._excess_history.clear()
            async_dispatcher_send(self.hass, self._signal_name, 0.0, 0)
            return
            
        grid_state = self.hass.states.get(self.conf["grid_sensor"])
        ev_state = self.hass.states.get(self.conf["ev_sensor"])
        volt_state = self.hass.states.get(self.conf["voltage_sensor"])
        batt_state = self.hass.states.get(self.conf["battery_sensor"])
        
        try:
            grid = float(grid_state.state) if grid_state else 0.0
            ev = float(ev_state.state) if ev_state else 0.0
            voltage = float(volt_state.state) if volt_state else 240.0
            battery_kw = float(batt_state.state) if batt_state else 0.0
        except ValueError:
            return
            
        battery_w = battery_kw * 1000
        battery_discharge_w = min(0, battery_w)
            
        # 2. CALCULATE LIVE EXCESS
        raw_excess_watts = (grid * -1) + ev + battery_discharge_w 
        
        # 3. ROLLING AVERAGE (Data Smoothing)
        now = time.time()
        self._excess_history.append((now, raw_excess_watts))
        # Keep only the last 2 minutes of data
        self._excess_history = [(t, w) for t, w in self._excess_history if now - t <= self._history_window]
        avg_excess_watts = sum(w for t, w in self._excess_history) / len(self._excess_history)
        
        target_amps = math.floor(avg_excess_watts / voltage)
        clamped_amps = max(0, min(32, target_amps))
        
        # 4. THE DEADBAND (Only react to changes of 2 Amps or more, unless shutting down)
        if self._current_amps is not None and clamped_amps >= 5:
            if abs(clamped_amps - self._current_amps) < 2:
                clamped_amps = self._current_amps # Force it to stay the same
                
        # Send smoothed data to UI Sensors
        async_dispatcher_send(self.hass, self._signal_name, avg_excess_watts, clamped_amps)
        
        # 5. THE TIMERS
        if clamped_amps == self._current_amps:
            if self._adjust_task:
                self._adjust_task.cancel()
                self._adjust_task = None
                self._pending_amps = None
            return
            
        if clamped_amps == self._pending_amps:
            return
            
        if self._adjust_task:
            self._adjust_task.cancel()
            
        self._pending_amps = clamped_amps
        
        # Start the massive 5-MINUTE (300 seconds) API & Contactor buffer
        self._adjust_task = self.hass.async_create_task(self._apply_changes_after_delay(clamped_amps, 300))

    async def _apply_changes_after_delay(self, target_amps, delay_seconds):
        try:
            _LOGGER.debug(f"Starting {delay_seconds}s delay for {target_amps}A...")
            
            await asyncio.sleep(delay_seconds)
            
            if not self._is_on:
                return 
                
            charge_switch = self.hass.states.get(self.conf["tesla_switch"])
            
            if target_amps >= 5:
                if charge_switch and charge_switch.state != STATE_ON:
                    _LOGGER.info(f"{delay_seconds}s passed. Waking Tesla.")
                    await self.hass.services.async_call("switch", "turn_on", {"entity_id": self.conf["tesla_switch"]})
                    
                if self._current_amps != target_amps:
                    _LOGGER.info(f"{delay_seconds}s passed. Changing limit to {target_amps}A.")
                    await self.hass.services.async_call("number", "set_value", {
                        "entity_id": self.conf["tesla_amps"],
                        "value": target_amps
                    })
                    self._current_amps = target_amps
            else:
                if charge_switch and charge_switch.state != STATE_OFF:
                    _LOGGER.info(f"{delay_seconds}s passed. Pausing Tesla.")
                    await self.hass.services.async_call("switch", "turn_off", {"entity_id": self.conf["tesla_switch"]})
                    self._current_amps = None
                    
            self._pending_amps = None
            
        except asyncio.CancelledError:
            _LOGGER.debug(f"Delay for {target_amps}A cancelled (sun recovered).")
