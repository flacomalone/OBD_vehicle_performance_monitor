from enum import IntEnum

class ParameterType(IntEnum):
    UDS = 1
    OBD = 2


class importantParameters():
    def __init__(self, name, address, pid, start, length, parameterType: ParameterType = ParameterType.UDS, mode=None,
                 unit=None, scalar=None, lookup_table=None):
        self.name = name
        self.address = address
        self.pid = pid
        self.start = start
        self.length = length
        self.parameterType = parameterType
        if self.parameterType == ParameterType.OBD:
            self.mode = mode
        if unit:
            self.unit = unit
        else:
            self.unit = ""
        if scalar:
            self.scalar = scalar
        else:
            self.scalar = 1
        self.lookup_table = lookup_table

    def converter(self, value):

        ## -------------------- No transformations --------------------

        if self.name in ["total_distance_travelled", "target_engine_revolution", "exhausts_co2_concentration"]:
            return int(value)

        ## -------------------- linear transformations --------------------

        elif self.name in ["target_engine_power", "execute_engine_power", "engine_speed", "hybrid_battery_voltage",
                           "engine_exhaust_flow_rate", "vehicle_fuel_rate", "engine_fuel_rate", "vehicle_speed",
                           "mass_air_flow", "calculate_load", "atmospheric_pressure", "co2_emissions_prediction",
                           "accelerator_position"]:
            return int(value, 16) * self.scalar
        elif self.name == "hybrid_battery_soc":
            return round(int(value, 16) * self.scalar, 2)  # I still want to keep the round function for battery SOC
        elif self.name == "coolant_temperature":
            return int(value, 16) - 40
        elif self.name == "deceleration_sensor":
            return int(value, 16) * 36.36 / 255 - 18.18
        elif self.name == "motor_revolution":
            h = int(value[0:2], 16)
            l = int(value[2:4], 16)
            return (h * 256 + l) - 32768
        elif self.name == "motor_torque":
            h = int(value[0:2], 16)
            l = int(value[2:4], 16)
            return (h * 256 + l) / 8 - 4096
        elif self.name == "hybrid_battery_current":
            h = int(value[0:2], 16)
            l = int(value[2:4], 16)
            if h != 255:  # positive current
                return l * self.scalar
            else:  # negative current (engine ON)
                return l * self.scalar * -0.5


        ## -------------------- Table lookup --------------------

        elif self.name in ["drive_mode", "ev_mode_status", "engine_mode", "lack_of_fuel", "powertrain_mode_switch",
                           "p_control_request_status"]:
            return int(value, 16)
            # return self.lookup_table[value]

        ## -------------------- To be confirmed / wrong transformation --------------------
        elif self.name == "ac_consumption_power":
            return int(value, 16) * 50 * 0.001341022089595  # To be confirmed, but irrelevant value
        elif self.name == "fuel_input_volume":
            return (int(value, 16) * 500 / 3785) / 1.2
        else:
            return int(value, 16)


EV_mode_status_lookup_table = {
    128: "Normal mode",
    129: "EV mode",
    130: "Automatic change to Normal mode: low battery",
    # Triggered when battery SOC falls to 13.33 % and cannot handle EV mode anymore.
    132: "EV CITY mode",
    133: "Automatic change to EV mode: work too demanding for EV CITY mode",
    # Potentially can be triggered when EV CITY cannot handle with targeted power (W) requested. This mode should perform no more than 53 kW
    135: "Battery charge mode",
    136: "Automatic change to Normal mode: battery too charged",
    # Triggered when battery SOC is higher or equal to 68.21 %
    137: "Standby for battery"
}
Drive_mode_lookup_table = {
    1: "EV mode",
    2: "HV mode",
    3: "Battery charge mode denied"  # When I cannot switch to EV mode due to lack of battery
}
Engine_mode_lookup_table = {
    0: "Stop",
    1: "Stop process",
    2: "Startup process",
    3: "Running"
}

Lack_of_fuel_lookup_table = {
    1: "OFF",
    0: "ON"  # #To be confirmed
}

Powertrain_mode_switch_lookup_table = {
    1: "OFF",
    0: "ON"
}

P_control_request_status = {
    3: "Lock",
    4: "Unlock"
}

# NOTE: The attributes "address", "PID" and "scalar" of the object of type "ImportantParameters" have been modified to irrelevant values due to IPR concerns.

parameters = {
    # UDS-based parameters
    ## UDS ECU 0x7D2s
    "ac_consumption_power": importantParameters("ac_consumption_power", 0x000, 0x0000, 1, 1, unit="kW"),
    # Scalar to be confirmed
    "drive_mode": importantParameters("drive_mode", 0x000, 0x10e5, 1, 1, lookup_table=Drive_mode_lookup_table),
    "deceleration_sensor": importantParameters("deceleration_sensor", 0x000, 0x0000, 1, 1, unit="m/s^2"),
    "engine_mode": importantParameters("engine_mode", 0x000, 0x0000, 1, 1, lookup_table=Engine_mode_lookup_table),
    "engine_speed": importantParameters("engine_speed", 0x000, 0x0000, 1, 2, unit="rpm", scalar=1),
    "ev_mode_status": importantParameters("ev_mode_status", 0x000, 0x0000, 1, 1, lookup_table=EV_mode_status_lookup_table),
    "execute_engine_power": importantParameters("execute_engine_power", 0x000, 0x0000, 3, 2, unit="KW", scalar=1),
    "hybrid_battery_current": importantParameters("hybrid_battery_current", 0x000, 0x0000, 5, 2, unit="A", scalar=1),
    "hybrid_battery_soc": importantParameters("hybrid_battery_soc", 0x000, 0x0000, 1, 1, unit="%", scalar=1),
    "hybrid_battery_voltage": importantParameters("hybrid_battery_voltage", 0x000, 0x0000, 3, 2, unit="V",scalar=1),
    "lack_of_fuel": importantParameters("lack_of_fuel", 0x7D2, 0x000, 2, 1, lookup_table=Lack_of_fuel_lookup_table),
    "motor_revolution": importantParameters("motor_revolution", 0x000, 0x0000, 1, 2, unit="rpm"),
    "motor_torque": importantParameters("motor_torque", 0x000, 0x0000, 7, 2, unit="Nm"),
    "p_control_request_status": importantParameters("p_control_request_status", 0x000, 0x0000, 2, 1,lookup_table=P_control_request_status),
    "powertrain_mode_switch": importantParameters("powertrain_mode_switch", 0x000, 0x0000, 2, 1,lookup_table=Powertrain_mode_switch_lookup_table),
    "target_engine_power": importantParameters("target_engine_power", 0x000, 0x0000, 1, 2, unit="KW", scalar=1),
    "target_engine_revolution": importantParameters("target_engine_revolution", 0x000, 0x0000, 1, 2, unit="rpm"),
    "accelerator_position": importantParameters("accelerator_position", 0x000, 0x0000, 1, 1, unit="%", scalar=1),

    ## UDS ECU 0x700
    "atmospheric_pressure": importantParameters("atmospheric_pressure", 0x000, 0x0000, 1, 1, unit="psi",scalar=1),
    "calculate_load": importantParameters("calculate_load", 0x000, 0x0000, 1, 1, unit="%", scalar=1),
    "coolant_temperature": importantParameters("coolant_temperature", 0x000, 0x0000, 1, 1, unit="C"),
    "engine_exhaust_flow_rate": importantParameters("engine_exhaust_flow_rate", 0x000, 0x0000, 1, 2, unit="Kg/h",scalar=1),
    "engine_fuel_rate": importantParameters("engine_fuel_rate", 0x000, 0x0000, 1, 2, unit="l/min",scalar=1),
    "mass_air_flow": importantParameters("mass_air_flow", 0x000, 0x0000, 1, 2, unit="g/min", scalar=1),
    "total_distance_travelled": importantParameters("total_distance_travelled", 0x000, 0x0103, 2, 3, unit="miles"),
    "vehicle_fuel_rate": importantParameters("vehicle_fuel_rate", 0x000, 0x0000, 3, 2, unit="l/min",scalar=1),
    "vehicle_speed": importantParameters("vehicle_speed", 0x000, 0x0000, 1, 1, unit="MPH", scalar=1),

    ## UDS ECU 0x7F0
    "exhausts_co2_concentration": importantParameters("exhausts_co2_concentration", 0x000, 0x0000, 1, 3, unit="PPM"),

    ## UDS ECU 0x7F2
    "co2_emissions_prediction": importantParameters("co2_emissions_prediction", 0x000, 0x0000, 1, 3, unit="g/s", scalar=1),

    # OBD-based parameters
    ## OBD ECU 0x7C0
    "fuel_input_volume": importantParameters("fuel_input_volume", 0x000, 0x00, 1, 1, parameterType=ParameterType.OBD, mode=0x21, unit="Imperial Gallons"),
}