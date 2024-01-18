import time
from statistics import mean

from panda.python import Panda
from lib.parameters import (parameters as IP)
from lib.protocols.UDS import UdsClient, NegativeResponseError, DYNAMIC_DEFINITION_TYPE, \
    SESSION_TYPE
from lib.protocols.ISOTP import MessageTimeoutError


dynamicAddresses_lookup = {
    0x700: 0xf301,  # 1792: 62209
    0x7D2: 0xf302,  # 2002: 62210
}


## This one is just for getting a single parameter at a time
def readDataByIdentifier(uds_client, parameter, loop: bool = True, sleep: float = None, raw_debug: bool = False,
                         debug: bool = False):
    while 1:
        try:
            response = uds_client.read_data_by_identifier(parameter.pid)
            start_value = 4 + ((parameter.start - 1) * 2)
            if raw_debug:
                print(response)
            value = response[start_value: start_value + parameter.length * 2]
            value = parameter.converter(int(value, 16))
            if debug:
                print(parameter.name, ": ", value, " ", parameter.unit, " | ", response)
            if not loop:
                break
            if sleep is not None:
                time.sleep(sleep)
        except NegativeResponseError:
            print("Negative response error for service ID: ", NegativeResponseError.service_id, " with error code: ",
                  NegativeResponseError.error_code)
            exit(-1)
        except MessageTimeoutError:
            print("MessageTimeout Error in ReadDataByIdentifier for parameter identifier", parameter.pid,
                  "(", parameter.name, ")")
    return value


def readDataByIdentifierTechstream(uds_client: object, loop: bool = True, sleep: float = 0.3, raw_debug: bool = False):
    while 1:
        try:
            response = uds_client.read_data_by_identifier([0xf301])
            if raw_debug:
                print(response)
            if not loop:
                break
            time.sleep(sleep)
        except NegativeResponseError:
            print("Negative response error for service ID: ", NegativeResponseError.service_id, " with error code: ",
                  NegativeResponseError.error_code)
        except MessageTimeoutError:
            print("MessageTimeout Error in ReadDataByIdentifier using Techstream")
            exit(-1)


def create_extendedDiagnosticSession(uds_client):
    try:
        uds_client.diagnostic_session_control(session_type=SESSION_TYPE.EXTENDED_DIAGNOSTIC)
    except MessageTimeoutError:
        print("MessageTimeout Error in diagnosticSessionControl")
        exit(-1)


def clearPreviousDynamicallyDefinedDataIdentifier(uds_client, data_identifier):
    try:
        uds_client.dynamically_define_data_identifier(
            dynamic_data_identifier=data_identifier,
            dynamic_definition_type=DYNAMIC_DEFINITION_TYPE.CLEAR_DYNAMICALLY_DEFINED_DATA_IDENTIFIER,
            start_point=None,
            length=None,
            source_definitions=None)
    except MessageTimeoutError:
        print("MessageTimeout Error in DynamicallyDefinedDataIdentifier")
        exit(-1)


def createDynamicallyDefinedDataIdentifierByParameterId(uds_client, data_identifier, parameters_list):
    try:
        uds_client.dynamically_define_data_identifier(
            dynamic_definition_type=DYNAMIC_DEFINITION_TYPE.DEFINE_BY_IDENTIFIER,
            dynamic_data_identifier=data_identifier,
            source_definitions=[p.pid for p in parameters_list],
            start_point=[p.start for p in parameters_list],
            length=[p.length for p in parameters_list])
    except MessageTimeoutError:
        print("MessageTimeout Error in DynamicallyDefinedDataIdentifier")
        exit(-1)


def prepareDynamicallyDefinedData(client, parameters_list):  # One per ECU address
    address = dynamicAddresses_lookup[client.tx_addr]
    # Create extended diagnostic session
    create_extendedDiagnosticSession(uds_client=client)
    # Clear previous DynamicallyDefinedDataIdentifier
    clearPreviousDynamicallyDefinedDataIdentifier(client, data_identifier=address)
    # Create new DynamicallyDefinedDataIdentifier with params
    createDynamicallyDefinedDataIdentifierByParameterId(client, data_identifier=address, parameters_list=parameters_list)


## This one is the one to be used when querying more than one parameter at a time (must prepare group first)
def readDataByIdentifier_dynamicallyAllocated(uds_client: UdsClient, parameter_list: list, loop: bool = True,
                                              sleep: float = None, raw_debug: bool = False, debug: bool = False):
    values_dict = dict.fromkeys([p.name for p in parameter_list])
    while 1:
        dynamically_allocated_id = dynamicAddresses_lookup[uds_client.tx_addr]
        response = uds_client.read_data_by_identifier(dynamically_allocated_id)
        try:

            if raw_debug:
                print(response)

            start_value = 4
            for p in parameter_list:
                value = response[start_value: start_value + p.length * 2]
                values_dict[p.name] = p.converter(value)

                # Start from last one + length of value * 2 + following data identifier
                start_value = start_value + p.length * 2
            if debug:
                print(values_dict)

            if not loop:
                break

            if sleep is not None:
                time.sleep(sleep)

        except MessageTimeoutError:
            print("MessageTimeout Error in ReadDataByIdentifier")
            exit(-1)

    return values_dict


def measureLatency():
    panda = Panda()
    panda.set_safety_mode(Panda.SAFETY_ALLOUTPUT)
    panda.set_power_save(False)
    bus = 0
    panda.can_clear(bus)

    parameters_list_7D2 = [IP.get(key) for key in
                           ["deceleration_sensor", "engine_mode", "engine_speed", "hybrid_battery_soc",
                            "vehicle_speed"]]
    parameters_list_700 = [IP.get(key) for key in ["coolant_temperature", "engine_exhaust_flow_rate", "mass_air_flow"]]
    parameters_list_7F0 = [IP.get(key) for key in ["exhausts_co2_concentration"]]

    client_7D2 = UdsClient(panda, parameters_list_7D2[0].address, bus, timeout=0.2, debug=False)
    client_700 = UdsClient(panda, parameters_list_700[0].address, bus, timeout=0.2, debug=False)
    client_7F0 = UdsClient(panda, parameters_list_7F0[0].address, bus, timeout=0.2, debug=False)

    prepareDynamicallyDefinedData(client_7D2, parameters_list_7D2)
    prepareDynamicallyDefinedData(client_700, parameters_list_700)

    times_single_query = []
    for i in range(100):
        start = time.time()
        readDataByIdentifier_dynamicallyAllocated(uds_client=client_7D2, parameter_list=parameters_list_7D2,
                                                  loop=False, debug=True)
        readDataByIdentifier_dynamicallyAllocated(uds_client=client_700, parameter_list=parameters_list_700,
                                                  loop=False, debug=True)
        readDataByIdentifier(uds_client=client_7F0, parameter=parameters_list_7F0[0], loop=False, debug=True)
        times_single_query.append(time.time() - start)
    print("time taken with single query:" + str(mean(times_single_query)))

    times_multiple_query = []
    for i in range(100):
        start = time.time()
        for p in parameters_list_7D2:
            readDataByIdentifier(client_7D2, p, loop=False, debug=True)
        for p in parameters_list_700:
            readDataByIdentifier(client_700, p, loop=False, debug=True)
        for p in parameters_list_7F0:
            readDataByIdentifier(client_7F0, p, loop=False, debug=True)
        times_multiple_query.append(time.time() - start)

    print("time taken with multiple query:" + str(mean(times_multiple_query)))


def little_test():
  panda = Panda()
  panda.set_safety_mode(Panda.SAFETY_ALLOUTPUT)
  panda.set_power_save(False)
  bus = 0
  panda.can_clear(bus)
  parameters_list_700 = [IP.get(key) for key in
                         ["engine_exhaust_flow_rate", "vehicle_speed", "coolant_temperature", "mass_air_flow"]]
  parameters_list_7D2 = [IP.get(key) for key in
                         ["deceleration_sensor", "engine_mode", "engine_speed", "hybrid_battery_soc", "hybrid_battery_current"]]

  client_700 = UdsClient(panda, 0x700, bus, timeout=2, debug=True)
  client_7D2 = UdsClient(panda, 0x7D2, bus, timeout=2, debug=False)

  prepareDynamicallyDefinedData(client_700, parameters_list_700)
  prepareDynamicallyDefinedData(client_7D2, parameters_list_7D2)

  for i in range(10):
    readDataByIdentifier_dynamicallyAllocated(uds_client=client_700, parameter_list=parameters_list_700,
                                              loop=False, debug=True)

    readDataByIdentifier_dynamicallyAllocated(uds_client=client_7D2, parameter_list=parameters_list_7D2,
                                              loop=False, debug=True)


def requestCO2_CAN():
  panda = Panda()
  client = UdsClient(panda, 0x7F0, 0, timeout=10, debug=False)
  while True:
    val = readDataByIdentifier(uds_client=client, parameter=IP["exhausts_co2_concentration"], loop=False, debug=False)
    print(val)



if __name__ == "__main__":
  requestCO2_CAN()
  #little_test()
  #measureLatency()
