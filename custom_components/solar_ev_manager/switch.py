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
        
        # Tracking Variables for Debouncing
        self._current_amps = None
        self._pending_amps = None
        self._adjust_task = None
        
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
        
        # Listen to all 5 required sensors
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
            
        # Cancel any pending 10-second timers when turning off
        if self._adjust_task:
            self._adjust_task.cancel()
            self._adjust_task = None
        self._pending_amps = None
            
        # Flatline UI sensors
        async_dispatcher_send(self.hass, self._signal_name, 0.0, 0)
            
        await self.hass.services.async_call("switch", "turn_on", {"entity_id": self.conf["octopus_switch"]})
        await self.hass.services.async_call("switch", "turn_off", {"entity_id": self.conf["tesla_switch"]})

    async def _calculate_and_adjust(self, event):
        if not self._is_on:
            return
            
        # ==========================================
        # 1. THE STRICT CABLE SHIELD ("Allow-List")
        # ==========================================
        cable_state = self.hass.states.get(self.conf["tesla_cable"])
        
        if cable_state and cable_state.state.lower() != "connected":
            _LOGGER.debug(f"Tesla cable is '{cable_state.state}'. Waiting for 'Connected'.")
            
            # Instantly cancel any running 10-second timers if unplugged
            if self._adjust_task:
                self._adjust_task.cancel()
                self._adjust_task = None
                self._pending_amps = None
                
            # Flatline the UI sensors so it shows 0 on the dashboard
            async_dispatcher_send(self.hass, self._signal_name, 0.0, 0)
            return
        # ==========================================
            
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
            
        # Battery Math (kW to W, and isolate discharge)
        battery_w = battery_kw * 1000
        battery_discharge_w = min(0, battery_w)
            
        # Total Excess Calculation
        excess_watts = (grid * -1) + ev + battery_discharge_w 
        
        target_amps = math.floor(excess_watts / voltage)
        clamped_amps = max(0, min(32, target_amps))
        
        # Update the UI Sensors immediately so you see the live math
        async_dispatcher_send(self.hass, self._signal_name, excess_watts, clamped_amps)
        
        # ==========================================
        # 2. THE DEBOUNCE LOGIC
        # ==========================================
        
        # If the car is already at this exact target, cancel any running timers.
        if clamped_amps == self._current_amps:
            if self._adjust_task:
                self._adjust_task.cancel()
                self._adjust_task = None
                self._pending_amps = None
            return
            
        # If we already have a timer running for this exact target, let it keep counting.
        if clamped_amps == self._pending_amps:
            return
            
        # Brand new target: cancel old timers and start a new 10-second countdown.
        if self._adjust_task:
            self._adjust_task.cancel()
            
        self._pending_amps = clamped_amps
        self._adjust_task = self.hass.async_create_task(self._apply_changes_after_delay(clamped_amps))

    # ==========================================
    # 3. THE TIMER FUNCTION
    # ==========================================
    async def _apply_changes_after_delay(self, target_amps):
        try:
            _LOGGER.debug(f"Starting 10-second delay for target {target_amps}A...")
            
            # Wait exactly 10 seconds.
            await asyncio.sleep(10)
            
            if not self._is_on:
                return # Abort if the master switch was turned off during the 10 seconds
                
            charge_switch = self.hass.states.get(self.conf["tesla_switch"])
            
            if target_amps >= 5:
                if charge_switch and charge_switch.state != STATE_ON:
                    _LOGGER.info("10s passed. Waking Tesla.")
                    await self.hass.services.async_call("switch", "turn_on", {"entity_id": self.conf["tesla_switch"]})
                    
                if self._current_amps != target_amps:
                    _LOGGER.info(f"10s passed. Changing Tesla limit to {target_amps}A.")
                    await self.hass.services.async_call("number", "set_value", {
                        "entity_id": self.conf["tesla_amps"],
                        "value": target_amps
                    })
                    self._current_amps = target_amps
            else:
                if charge_switch and charge_switch.state != STATE_OFF:
                    _LOGGER.info("10s passed. Pausing Tesla.")
                    await self.hass.services.async_call("switch", "turn_off", {"entity_id": self.conf["tesla_switch"]})
                    self._current_amps = None
                    
            # Clear the pending flag now that it's applied
            self._pending_amps = None
            
        except asyncio.CancelledError:
            _LOGGER.debug(f"10-second delay for {target_amps}A was CANCELLED (sun/cable changed).")
