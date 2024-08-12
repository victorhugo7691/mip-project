"""
Defines the input and output schemas of the problem.
For more details on how to implement and configure data schemas see:
https://github.com/mipwise/mip-go/tree/main/5_develop/4_data_schema
"""

from ticdat import PanDatFactory
from mip_procure.constants import SiteTypes


# region Aliases for datatypes in ticdat
# Remark: use only aliases that match perfectly your needs, otherwise set datatype explicitly
float_number = {
    "number_allowed": True,
    "strings_allowed": (),
    "must_be_int": False,
    "min": -float("inf"),
    "inclusive_min": False,
    "max": float("inf"),
    "inclusive_max": False,
}

non_negative_float = {
    "number_allowed": True,
    "strings_allowed": (),
    "must_be_int": False,
    "min": 0,
    "inclusive_min": True,
    "max": float("inf"),
    "inclusive_max": False,
}

positive_float = {
    "number_allowed": True,
    "strings_allowed": (),
    "must_be_int": False,
    "min": 0,
    "inclusive_min": False,
    "max": float("inf"),
    "inclusive_max": False,
}

integer_number = {
    "number_allowed": True,
    "strings_allowed": (),
    "must_be_int": True,
    "min": -float("inf"),
    "inclusive_min": False,
    "max": float("inf"),
    "inclusive_max": False,
}

non_negative_integer = {
    "number_allowed": True,
    "strings_allowed": (),
    "must_be_int": True,
    "min": 0,
    "inclusive_min": True,
    "max": float("inf"),
    "inclusive_max": False,
}

positive_integer = {
    "number_allowed": True,
    "strings_allowed": (),
    "must_be_int": True,
    "min": 1,
    "inclusive_min": True,
    "max": float("inf"),
    "inclusive_max": False,
}

binary = {
    "number_allowed": True,
    "strings_allowed": (),
    "must_be_int": True,
    "min": 0,
    "inclusive_min": True,
    "max": 1,
    "inclusive_max": True,
}

text = {"strings_allowed": "*", "number_allowed": False}
# endregion

# region INPUT SCHEMA
input_schema = PanDatFactory(
    parameters=[['Name'], ['Value']],  # Do not change the column names of the parameters table!
    time_periods=[['Period ID'], ['Start Date', 'End Date']],
    sites=[['Site ID'], ['Site Name', 'Site Type']],
    items=[['Item ID'], ['Item Name', 'Min Order Qty.', 'Max Order Qty.', 'Min Transfer Qty.']],
    procurement_costs=[['Item ID', 'Period ID'], ['Unit Cost']],
    demand=[['Item ID', 'Period ID'], ['Demand Qty.', 'Min Inventory']],
    inventory=[['Item ID', 'Site ID'], ['Opening Inventory', 'Unit Holding Cost']],
)
# endregion

# region USER PARAMETERS
input_schema.add_parameter('Max Aging Time', default_value=7, **non_negative_integer)
input_schema.add_parameter('Supplier Expedition Capacity', default_value=6_000, **non_negative_float)
input_schema.add_parameter('Warehouse Receiving Capacity', default_value=20, **non_negative_float)
input_schema.add_parameter('Supplier Inventory Capacity', default_value=1_000_000, **non_negative_float)
input_schema.add_parameter('Warehouse Inventory Capacity', default_value=550_000, **non_negative_float)
# endregion

# region OUTPUT SCHEMA
output_schema = PanDatFactory(
    kpis=[['KPI'], ['Value']],
    flow_supplier=[['Item ID', 'Period ID'], ['Initial Inventory', 'Order Qty.', 'Transferred Qty.', 'Final Inventory',
                                              'Unit Holding Cost', 'Holding Cost']],
    flow_warehouse=[['Item ID', 'Period ID'], ['Initial Inventory', 'Received Qty.', 'Demand Qty.', 'Final Inventory',
                                               'Min Inventory', 'Unit Holding Cost', 'Holding Cost']],
    orders=[['Order ID'], ['Item ID', 'Period ID', 'Order Qty.', 'Min Order Qty.', 'Max Order Qty.', 'Unit Cost',
                           'Order Cost']],
    shipments=[['Shipment ID'], ['Item ID', 'Period ID', 'Transferred Qty.', 'Min Transfer Qty.']],
    total_inventory=[['Site ID', 'Period ID'], ['Final Inventory', 'Inventory Capacity']]
)
# endregion

# region DATA TYPES AND PREDICATES - INPUT SCHEMA
# region time_periods
table = 'time_periods'
input_schema.set_data_type(table=table, field='Period ID', **integer_number)
input_schema.set_data_type(table=table, field='Start Date', datetime=True)
input_schema.set_data_type(table=table, field='End Date', datetime=True)
input_schema.add_data_row_predicate(table=table, predicate_name='Start Date <= End Date',
                                    predicate=lambda row: row['Start Date'] <= row['End Date'])
# endregion

# region sites
table = 'sites'
input_schema.set_data_type(table=table, field='Site ID', **text)
input_schema.set_data_type(table=table, field='Site Name', **text, nullable=True)
input_schema.set_data_type(table=table, field='Site Type', number_allowed=False, strings_allowed=tuple(SiteTypes))
# endregion

# region items
table = 'items'
input_schema.set_data_type(table=table, field='Item ID', **text)
input_schema.set_data_type(table=table, field='Item Name', **text, nullable=True)
input_schema.set_data_type(table=table, field='Min Order Qty.', **non_negative_float)
input_schema.set_data_type(table=table, field='Max Order Qty.', **non_negative_float)
input_schema.set_data_type(table=table, field='Min Transfer Qty.', **non_negative_float)
input_schema.add_data_row_predicate(table=table, predicate_name="Min Order Qty. <= Max Order Qty.",
                                    predicate=lambda row: row['Min Order Qty.'] <= row['Max Order Qty.'])
# endregion

# region procurement_costs
table = 'procurement_costs'
input_schema.set_data_type(table=table, field='Item ID', **text)
input_schema.set_data_type(table=table, field='Period ID', **integer_number)
input_schema.set_data_type(table=table, field='Unit Cost', **non_negative_float)
input_schema.add_foreign_key(native_table=table, foreign_table='items', mappings=['Item ID', 'Item ID'])
input_schema.add_foreign_key(native_table=table, foreign_table='time_periods', mappings=['Period ID', 'Period ID'])
# endregion

# region demand
table = 'demand'
input_schema.set_data_type(table=table, field='Item ID', **text)
input_schema.set_data_type(table=table, field='Period ID', **integer_number)
input_schema.set_data_type(table=table, field='Demand Qty.', **non_negative_float)
input_schema.set_data_type(table=table, field='Min Inventory', **non_negative_float)
input_schema.add_foreign_key(native_table=table, foreign_table='items', mappings=['Item ID', 'Item ID'])
input_schema.add_foreign_key(native_table=table, foreign_table='time_periods', mappings=['Period ID', 'Period ID'])
# endregion

# region inventory
table = 'inventory'
input_schema.set_data_type(table=table, field='Item ID', **text)
input_schema.set_data_type(table=table, field='Site ID', **text)
input_schema.set_data_type(table=table, field='Opening Inventory', **non_negative_float)
input_schema.set_data_type(table=table, field='Unit Holding Cost', **non_negative_float)
input_schema.add_foreign_key(native_table=table, foreign_table='items', mappings=['Item ID', 'Item ID'])
input_schema.add_foreign_key(native_table=table, foreign_table='sites', mappings=['Site ID', 'Site ID'])
# endregion

# endregion





# region DATA TYPES AND PREDICATES - OUTPUT SCHEMA

# region kpis
table = 'kpis'
output_schema.set_data_type(table=table, field='KPI', **text)
output_schema.set_data_type(table=table, field='Value', **float_number)
# endregion

# region flow_supplier
table = 'flow_supplier'
output_schema.set_data_type(table=table, field='Item ID', **text)
output_schema.set_data_type(table=table, field='Period ID', **integer_number)
output_schema.set_data_type(table=table, field='Initial Inventory', **non_negative_float)
output_schema.set_data_type(table=table, field='Order Qty.', **non_negative_float)
output_schema.set_data_type(table=table, field='Transferred Qty.', **non_negative_float)
output_schema.set_data_type(table=table, field='Final Inventory', **non_negative_float)
output_schema.set_data_type(table=table, field='Unit Holding Cost', **non_negative_float)
output_schema.set_data_type(table=table, field='Holding Cost', **non_negative_float)
# endregion

# region flow_warehouse
table = 'flow_warehouse'
output_schema.set_data_type(table=table, field='Item ID', **text)
output_schema.set_data_type(table=table, field='Period ID', **integer_number)
output_schema.set_data_type(table=table, field='Initial Inventory', **non_negative_float)
output_schema.set_data_type(table=table, field='Received Qty.', **non_negative_float)
output_schema.set_data_type(table=table, field='Demand Qty.', **non_negative_float)
output_schema.set_data_type(table=table, field='Final Inventory', **non_negative_float)
output_schema.set_data_type(table=table, field='Min Inventory', **non_negative_float)
output_schema.set_data_type(table=table, field='Unit Holding Cost', **non_negative_float)
output_schema.set_data_type(table=table, field='Holding Cost', **non_negative_float)
# endregion

# region orders
table = 'orders'
output_schema.set_data_type(table=table, field='Order ID', **text)
output_schema.set_data_type(table=table, field='Item ID', **text)
output_schema.set_data_type(table=table, field='Period ID', **integer_number)
output_schema.set_data_type(table=table, field='Order Qty.', **non_negative_float)
output_schema.set_data_type(table=table, field='Min Order Qty.', **non_negative_float)
output_schema.set_data_type(table=table, field='Max Order Qty.', **non_negative_float)
output_schema.set_data_type(table=table, field='Unit Cost', **non_negative_float)
output_schema.set_data_type(table=table, field='Order Cost', **non_negative_float)
# endregion

# region shipments
table = 'shipments'
output_schema.set_data_type(table=table, field='Shipment ID', **text)
output_schema.set_data_type(table=table, field='Item ID', **text)
output_schema.set_data_type(table=table, field='Period ID', **integer_number)
output_schema.set_data_type(table=table, field='Transferred Qty.', **non_negative_float)
output_schema.set_data_type(table=table, field='Min Transfer Qty.', **non_negative_float)
# endregion

# region total_inventory
table = 'total_inventory'
output_schema.set_data_type(table=table, field='Site ID', **text)
output_schema.set_data_type(table=table, field='Period ID', **integer_number)
output_schema.set_data_type(table=table, field='Final Inventory', **non_negative_float)
output_schema.set_data_type(table=table, field='Inventory Capacity', **non_negative_float)
# endregion

# endregion

