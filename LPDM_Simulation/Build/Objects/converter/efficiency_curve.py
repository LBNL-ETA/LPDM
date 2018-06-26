
class EfficiencyCurve:
    def __init__(self, efficiency_curve_data, capacity):
        self._curve_data = efficiency_curve_data
        self._capacity = capacity
    
    def calculate_power_loss(self, load, max_load):
        "calculate the power loss percentage based on the percent of capacity used"
        eff_prev = {"capacity": 0.0, "efficiency": 0.0}
        eff = None
        for item in self._curve_data:
            eff = item
            if load <= item["capacity"]:
                break
            eff_prev = eff
        return load - load * ((eff["efficieny"] - eff_prev["efficiency"]) / (eff["capacity"] - eff_prev["capacity"]))
    
    def calculate_efficiency(self, load):
        eff_prev = {"capacity": 0.0, "efficiency": 0.0}
        eff = None
        for item in self._curve_data:
            eff = item
            if load <= item["capacity"]:
                break
            eff_prev = eff
        return load * ((eff["efficieny"] - eff_prev["efficiency"]) / (eff["capacity"] - eff_prev["capacity"]))
    
    def get_efficiency_inputs(self, percent_capacity):
        "Find the surrounding efficiency curve items"
        ef_1 = None
        ef_2 = None
        # if percent_capacity == 1:
        #     return (None, self._curve_data[-1])

        for ef in self._curve_data:
            if ef["capacity"] > percent_capacity:
                ef_2 = ef
                break
            elif ef["capacity"] == percent_capacity:
                ef_2 = ef
                ef_1 = None
                break
            ef_1 = ef
        return (ef_1, ef_2)
    
    def get_efficiency_value(self, load):
        "Calculate the efficiency value based on the load relative to the capacity"
        percent_capacity = abs(load) / self._capacity
        (ef_1, ef_2) = self.get_efficiency_inputs(percent_capacity)
        if not ef_1:
            return ef_2["efficiency"]
        elif not ef_2:
            return ef_1["efficiency"]
        else:
            dydx = ((ef_2["efficiency"] - ef_1["efficiency"]) / (ef_2["capacity"] - ef_1["capacity"]))
            return (ef_1["efficiency"] + (percent_capacity - ef_1["capacity"]) * dydx)
    
    def get_converter_loss(self, load):
        "Calculate the power loss through the converter"
        # load is the output power of the converter
        # return load - (self.get_efficiency_value(load) * load)
        eff = self.get_efficiency_value(load)
        if eff <= 0:
            return load
        elif eff >= 1:
            return 0
        else:
            input_power = load / eff
            return abs(input_power) - abs(load)

    # def get_converter_loss_source(self, source):
    #     "Calculate the power loss through the converter"
    #     # source is the input power of the converter
    #     eff = self.get_efficiency_value(source)
    #     if eff <= 0:
    #         return load
    #     elif eff >= 1:
    #         return 0
    #     else:
    #         # try to find output power by iterative method
    #         output_power = source * eff
    #         for n in range(0,10):
    #             eff = self.get_efficiency_value(output_power)
    #             output_power = source * eff
    #         return abs(source) - abs(output_power)



