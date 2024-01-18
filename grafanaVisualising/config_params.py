from lib.parameters import parameters as P

# Defines the frequency (Hz) at which the data is collected
samplingRate = 20

# Comment and uncomment the params that are going to be collected from the vehicle

############## PRIMARY PARAMETERS ##########

# Query parameters definition divided by ECU query address
parametersToQuery_0x700 = [  # Engine
    ### P["atmospheric_pressure"],
    ### P["calculate_load"],
    P["coolant_temperature"],
    P["engine_exhaust_flow_rate"],
    P["mass_air_flow"],
    ### P["total_distance_travelled"],
    P["vehicle_fuel_rate"],
]

parametersToQuery_0x7D2 = [  # Hybrid System
    ### P["accelerator_position"],
    ### P["ac_consumption_power"], # Not useful
    ### P["drive_mode"],
    P["deceleration_sensor"],
    P["engine_mode"],
    P["engine_speed"],
    ### P["ev_mode_status"],
    ### P["execute_engine_power"],
    P["hybrid_battery_current"], # Not useful
    P["hybrid_battery_soc"],
    P["hybrid_battery_voltage"], # Not useful
    ### P["lack_of_fuel"],
    ### P["motor_revolution"],
    ### P["motor_torque"],
    ### P["p_control_request_status"], # Not useful
    ### P["powertrain_mode_switch"], # Not useful
    ### P["target_engine_power"], # Not useful
    ### P["target_engine_revolution"], # Not useful
    P["vehicle_speed"],
]

parametersToQuery_0x7C0 = [  # Combination Meter
    ### P["fuel_input_volume"],
]

parametersToQuery_0x7F0 = [  # CO2 agent
    P["exhausts_co2_concentration"],
]

paramsToQuery = parametersToQuery_0x700 + parametersToQuery_0x7D2 + parametersToQuery_0x7C0 + parametersToQuery_0x7F0
paramsToQuery.sort(key=lambda x: x.name)  # sorted by name to facilitate logging in csv file:
primary_params = {}
for p in paramsToQuery:
    primary_params[p.name] = -1

############## SECONDARY PARAMETERS ##########

_secundary_params = [
    ### "co2_emissions",  # g/s
    ### "distance_travelled_since_startup",  # miles
    ### "fuel_used_since_startup", # (US Gallons) # It is not very useful
    ### "motor_power_delivered",  # KW
]
_secundary_params.sort()
secondary_params = {}
for p in _secundary_params:
    secondary_params[p] = -1
