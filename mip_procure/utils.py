from typing import Any, Dict, List

import pandas as pd
from ticdat import PanDatFactory


def set_input_parameter(schema, dat, name: str, value: Any):
    assert isinstance(schema, PanDatFactory)
    assert isinstance(dat, schema.PanDat)
    assert isinstance(name, str)

    if not (name in schema.parameters):
        raise ValueError(f"Parameter {repr(name)} not found in schema.")

    params_df: pd.DataFrame = dat.parameters.copy()
    _dat = schema.copy_pan_dat(dat)
    
    if name in params_df["Name"].values:
        print(f"Overwriting parameter {repr(name)} with new value {repr(value)}")
        params_df.loc[params_df["Name"] == name, "Value"] = value
    else:
        print(f"Adding new parameter {repr(name)} with value {repr(value)}")
        new_row = pd.DataFrame({"Name": [name], "Value": [value]})
        params_df = pd.concat([params_df, new_row], ignore_index=True, axis=0)
    
    _dat.parameters = params_df
    
    return _dat


def set_multiple_input_parameters(schema, dat, parameters: Dict[str, Any]):
    _dat = schema.copy_pan_dat(dat)
    
    for param_name, param_value in parameters.items():
        _dat = set_input_parameter(schema, _dat, param_name, param_value)

    return _dat


def is_list_of_consecutive_increasing_integers(list_of_integers: List[int]) -> bool:
    assert isinstance(list_of_integers, list)
    assert all(isinstance(value, int) for value in list_of_integers)
    return list_of_integers == list(range(min(list_of_integers), max(list_of_integers) + 1))


class BadSolutionError(Exception):
    """
    Raised inside DatOut when the optimization solution is not feasible.
    """
