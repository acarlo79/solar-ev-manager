import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import selector

DOMAIN = "solar_ev_manager"

class SolarEVManagerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="Solar EV Manager", data=user_input)

        data_schema = vol.Schema({
            vol.Required("grid_sensor"): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
            vol.Required("ev_sensor"): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
            vol.Required("voltage_sensor"): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
            vol.Required("battery_sensor"): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
            vol.Required("octopus_switch"): selector.EntitySelector(selector.EntitySelectorConfig(domain="switch")),
            vol.Required("tesla_switch"): selector.EntitySelector(selector.EntitySelectorConfig(domain="switch")),
            vol.Required("tesla_amps"): selector.EntitySelector(selector.EntitySelectorConfig(domain="number")),
            
            # THE FIX: Allow both standard sensors and binary sensors!
            vol.Required("tesla_cable"): selector.EntitySelector(selector.EntitySelectorConfig(domain=["sensor", "binary_sensor"])),
        })

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema
        )
