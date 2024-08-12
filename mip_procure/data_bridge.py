import itertools
import pandas as pd
import pulp as plp
from mip_procure.constants import SiteTypes
from mip_procure.schemas import input_schema, output_schema
from mip_procure.utils import BadSolutionError, is_list_of_consecutive_increasing_integers


class DatIn:
    """
    Class that prepares the data (from the input tables, stored in a PanDat object) to be consumed by the main engine.

    Every set and every parameter defined in the mathematical formulation is populated here from the input
    tables and set as an attribute of this class. As a result, the optimization model becomes identical
    to the mathematical formulation, which facilitates debugging and maintenance.
    """

    def __init__(self, dat: input_schema.PanDat, verbose: bool = False) -> None:
        """
        Initializes a DatIn instance, from a dat object.

        When a DatIn instance is initialized (i.e., when this method is called), we read the input data (tables as
        pandas dataframes, stored in the dat parameter) and populate all the optimization indices/parameters as
        instance attributes.

        Parameters
        ----------
        dat : input_schema.PanDat
            A PanDat object from ticdat package, created accordingly to schemas.input_schema. It contains the input 
            data as its attributes (pandas dataframes).
        """
        print('Instantiating a DatIn object...')
        self.dat = input_schema.copy_pan_dat(pan_dat=dat)  # copy input "dat" to avoid over-writing
        self.dat_params = input_schema.create_full_parameters_dict(dat)  # create input parameters from 'dat'

        # set of indices, populated in _populate_sets_of_indices() method
        self.I = set()  # set of items ids
        self.T = []  # list of time periods
        
        # parameters, populated in _populate_parameters() method
        self.t0 = None  # int, first time period
        self.ois = {}  # dict {i: opening_inventory_at_supplier}
        self.oi = {}  # dict {i: opening_inventory_at_warehouse}
        self.cis = {}  # dict {i: holding_unit_cost_at_supplier}
        self.ci = {}  # dict {i: holding_unit_cost_at_warehouse}
        self.il = {}  # dict {(i, t): min_inventory_at_warehouse}
        self.iu = {}  # dict {t: inventory_capacity_at_warehouse}
        self.ius = {}  # dict {t: inventory_capacity_at_supplier}
        self.d = {}  # dict {(i, t): demand_at_warehouse}
        self.moq = {}  # dict {i: min_order_quantity}
        self.maxoq = {}  # dict {i: max_order_quantity}
        self.mtq = {}  # dict {i: min_transfer_qty_from_supplier}
        self.pc = {}  # dict {(i, t): unit_procuremet_cost}
        self.tu = None  # int, max aging time
        self.ec = None  # float, expedition capacity
        self.rc = None  # int, receiving capacity
        
        # auxiliary data
        self.suppliers_ids = set()  # set of suppliers ids
        self.warehouses_ids = set()  # set of warehouses ids
        self.x_keys = []
        self.y_keys = []
        self.ys_keys = []
        self.z_keys = []
        self.w_keys = []
        self.zs_keys = []

        # populate optimization data. The order below in which methods are called is important! Don't change it!
        print("Populating the optimization data...")
        self._populate_sets_of_indices()
        self._populate_parameters()
        self._derive_variables_keys()

        if verbose:
            self.print_opt_data()

    def _populate_sets_of_indices(self) -> None:
        """
        Populates the set of indices I, T, and K, used to add constraints to the optimization model.
        """
        dat = self.dat
        self.I = set(dat.items['Item ID'])
        self.T = dat.time_periods['Period ID'].sort_values(ascending=True, ignore_index=True).to_list()
        if not is_list_of_consecutive_increasing_integers(self.T):
            raise ValueError("'Period ID' column in 'time_periods' table must contain consecutive integers.")

        self.suppliers_ids = set(dat.sites.loc[dat.sites['Site Type'] == SiteTypes.SUPPLIER, 'Site ID'])
        self.warehouses_ids = set(dat.sites.loc[dat.sites['Site Type'] == SiteTypes.WAREHOUSE, 'Site ID'])
        if (len(self.suppliers_ids) + len(self.warehouses_ids) >= 3):
            raise NotImplementedError("The model is not yet implemented for multi-suppliers and/or multi-warehouses.")

    def _populate_parameters(self) -> None:
        """
        Populate the parameters to be used when adding constraints and the objective function to the
        optimization model.
        """
        dat = self.dat

        # filter some input tables by splitting their data into Suppliers and Warehouses
        inventory_df_suppliers = dat.inventory[dat.inventory['Site ID'].isin(self.suppliers_ids)]
        inventory_df_warehouses = dat.inventory[dat.inventory['Site ID'].isin(self.warehouses_ids)]

        self.t0 = min(self.T)
        self.ois = dict(zip(inventory_df_suppliers['Item ID'], inventory_df_suppliers['Opening Inventory']))
        self.oi = dict(zip(inventory_df_warehouses['Item ID'], inventory_df_warehouses['Opening Inventory']))
        self.cis = dict(zip(inventory_df_suppliers['Item ID'], inventory_df_suppliers['Unit Holding Cost']))
        self.ci = dict(zip(inventory_df_warehouses['Item ID'], inventory_df_warehouses['Unit Holding Cost']))
        self.il = dict(zip(zip(dat.demand['Item ID'], dat.demand['Period ID']), dat.demand['Min Inventory']))
        self.iu = {t: self.dat_params['Warehouse Inventory Capacity'] for t in self.T}
        self.ius = {t: self.dat_params['Supplier Inventory Capacity'] for t in self.T}
        self.d = dict(zip(zip(dat.demand['Item ID'], dat.demand['Period ID']), dat.demand['Demand Qty.']))
        self.pc = dict(zip(
            zip(dat.procurement_costs['Item ID'], dat.procurement_costs['Period ID']),
            dat.procurement_costs['Unit Cost']
        ))
        self.moq = dict(zip(dat.items['Item ID'], dat.items['Min Order Qty.']))
        self.maxoq = dict(zip(dat.items['Item ID'], dat.items['Max Order Qty.']))
        self.mtq = dict(zip(dat.items['Item ID'], dat.items['Min Transfer Qty.']))
        self.tu = self.dat_params['Max Aging Time']
        self.ec = self.dat_params['Supplier Expedition Capacity']
        self.rc = self.dat_params['Warehouse Receiving Capacity']

    def _derive_variables_keys(self) -> None:
        I, T = self.I, self.T
        self.x_keys = [(i, t) for i in I for t in T]
        self.y_keys = [(i, t) for i in I for t in [self.t0-1] + T]
        self.ys_keys = self.y_keys.copy()
        self.z_keys = self.x_keys.copy()
        self.w_keys = [(i, t) for i in I for t in T]
        self.zs_keys = self.w_keys.copy()
        
    def print_opt_data(self) -> None:
        """
        Prints the indices/parameters created for the optimization engine.
        """
        for attr_name, value in self.__dict__.items():
            if attr_name.startswith('_'):
                continue
            print(f"{attr_name}:")
            print(value)
            print('-' * 40)


class DatOut:
    """
    Processes the output from the main engine and populates the output tables, stored as pandas dataframes
    (attributes of DatOut instances).

    The user can get a PanDat object containing the output dataframes by calling the build_output() method (which
    retrieves a PanDat), and/or print them through print_solution_dataframes() method.
    """

    def __init__(self, solution_model) -> None:
        """
        Initializes a DatOut instance from the solved optimization model, and populates the output tables.

        Parameters
        ----------
        solution_model : OptModel
            An instance of the OptModel class (see opt_model.py) which has already called its optimize() method. It
            contains the output data from optimization to feed the DatOut class.
        """
        print('Instantiating a DatOut object...')
        # get optimal data
        self.solution_model = solution_model
        self.opt_sol = solution_model.sol
        self.dat_in: DatIn = solution_model.dat_in

        # initialize output data
        self.flow_supplier_df = None
        self.flow_warehouse_df = None
        self.orders_df = None
        self.shipments_df = None
        self.total_inventory_df = None
        self.kpis_df = None

        # populate the solution dataframes
        self._process_solution()

    def _process_solution(self) -> None:
        """
        Converts the output from the optimization into dataframes that will be used to build reports.
        """
        dat_in, dat = self.dat_in, self.dat_in.dat
        I, T = dat_in.I, dat_in.T

        # get solution status and whether the solution is good
        solution_status = self.opt_sol['status']
        is_feasible_solution = solution_status in [plp.LpStatusOptimal]

        if not is_feasible_solution:
            msg = f"Cannot process solution because it's not feasible. Solution status: {solution_status}"
            raise BadSolutionError(msg)

        # read output variables' values from optimization
        vars_sol = self.opt_sol['vars']
        x_sol = vars_sol['x']
        y_sol = vars_sol['y']
        z_sol = vars_sol['z']
        ys_sol = vars_sol['ys']
        w_sol = vars_sol['w']
        zs_sol = vars_sol['zs']
        kpis_sol = vars_sol['kpis']

        # create output dataframes
        # get sequence of items and time periods, ordered as they come from the input data
        items_sequence = dat.items['Item ID'].to_list()
        periods_sequence = dat.time_periods['Period ID'].to_list()
        all_items_periods_df = pd.DataFrame(
            data=itertools.product(items_sequence, periods_sequence),
            columns=['Item ID', 'Period ID']
        )
        all_items_periods_df = all_items_periods_df.astype({'Item ID': str, 'Period ID': int})

        # filter inventory by supplier and warehouse
        inventory_df_supplier = dat.inventory[dat.inventory['Site ID'].isin(dat_in.suppliers_ids)].copy()
        inventory_df_warehouse = dat.inventory[dat.inventory['Site ID'].isin(dat_in.warehouses_ids)].copy()

        # create orders dataframe
        x_df = pd.DataFrame(
            data=[(i, t, value) for (i, t), value in x_sol.items()],
            columns=['Item ID', 'Period ID', 'Order Qty.']
        )
        orders_df = x_df.merge(dat.items[['Item ID', 'Min Order Qty.', 'Max Order Qty.']], on='Item ID')
        orders_df = orders_df.merge(
            dat.procurement_costs[['Item ID', 'Period ID', 'Unit Cost']], on=['Item ID', 'Period ID'], how='left'
        )
        orders_df['Order Cost'] = orders_df['Order Qty.'] * orders_df['Unit Cost']
        orders_df = orders_df[['Item ID', 'Period ID', 'Order Qty.', 'Min Order Qty.', 'Max Order Qty.', 'Unit Cost',
                               'Order Cost']]
        orders_df = orders_df.astype({'Item ID': str, 'Period ID': int, 'Order Qty.': float, 'Min Order Qty.': float,
                                      'Max Order Qty.': float, 'Unit Cost': float, 'Order Cost': float})
        # sort values as they come from the input data by merging with all_items_periods_df
        orders_df = all_items_periods_df.merge(orders_df, on=['Item ID', 'Period ID'], how='inner')
        orders_df['Order ID'] = range(1, len(orders_df) + 1)
        orders_df['Order ID'] = orders_df['Order ID'].astype(str)
        self.orders_df = orders_df

        # create shipments dataframe
        w_df = pd.DataFrame(data=[(i, t, value) for (i, t), value in w_sol.items()],
                            columns=['Item ID', 'Period ID', 'Transferred Qty.'])
        shipments_df = w_df.merge(dat.items[['Item ID', 'Min Transfer Qty.']], on='Item ID', how='left')
        shipments_df = shipments_df.astype({'Item ID': str, 'Period ID': int, 'Transferred Qty.': float,
                                            'Min Transfer Qty.': float})
        # sort values as they come from the input data by merging with all_items_periods_df
        shipments_df = all_items_periods_df.merge(shipments_df, on=['Item ID', 'Period ID'], how='inner')
        shipments_df['Shipment ID'] = range(1, len(shipments_df) + 1)
        shipments_df = shipments_df.astype({'Shipment ID': str})
        self.shipments_df = shipments_df

        # create flow_supplier dataframe
        ys_df = pd.DataFrame(data=[(i, t, value) for (i, t), value in ys_sol.items()],
                             columns=['Item ID', 'Period ID', 'Final Inventory'])
        ys_df = ys_df.astype({'Item ID': str, 'Period ID': int, 'Final Inventory': float})
        
        # shift Final Inventory to create Initial Inventory, and fill missing values with Opening Inventory
        ys_df = ys_df.sort_values(by=['Item ID', 'Period ID'], ascending=True, ignore_index=True)
        ys_df['Initial Inventory'] = ys_df.groupby('Item ID')['Final Inventory'].shift(1)
        ys_df.loc[ys_df['Initial Inventory'].isna(), 'Initial Inventory'] = ys_df.loc[
            ys_df['Initial Inventory'].isna(), 'Item ID'
        ].map(dat_in.ois)
        
        flow_supplier_df = all_items_periods_df.merge(ys_df, on=['Item ID', 'Period ID'], how='left')
        flow_supplier_df = flow_supplier_df.merge(
            orders_df[['Item ID', 'Period ID', 'Order Qty.']], on=['Item ID', 'Period ID'], how='left'
        )
        flow_supplier_df['Order Qty.'] = flow_supplier_df['Order Qty.'].fillna(0)
        flow_supplier_df = flow_supplier_df.merge(
            shipments_df[['Item ID', 'Period ID', 'Transferred Qty.']], on=['Item ID', 'Period ID'], how='left'
        )
        flow_supplier_df['Transferred Qty.'] = flow_supplier_df['Transferred Qty.'].fillna(0)
        flow_supplier_df = flow_supplier_df.merge(
            inventory_df_supplier[['Item ID', 'Unit Holding Cost']], on='Item ID', how='left'
        )
        flow_supplier_df['Holding Cost'] = flow_supplier_df['Final Inventory'] * flow_supplier_df['Unit Holding Cost']
        flow_supplier_df = flow_supplier_df.astype({
            'Item ID': str, 'Period ID': int, 'Initial Inventory': float, 'Order Qty.': float,
            'Transferred Qty.': float, 'Final Inventory': float, 'Unit Holding Cost': float, 'Holding Cost': float
        })
        self.flow_supplier_df = flow_supplier_df

        # create flow_warehouse dataframe
        y_df = pd.DataFrame(data=[(i, t, value) for (i, t), value in y_sol.items()],
                            columns=['Item ID', 'Period ID', 'Final Inventory'])
        y_df = y_df.astype({'Item ID': str, 'Period ID': int, 'Final Inventory': float})
        
        # shift Final Inventory to create Initial Inventory, and fill missing values with Opening Inventory
        y_df = y_df.sort_values(by=['Item ID', 'Period ID'], ascending=True, ignore_index=True)
        y_df['Initial Inventory'] = y_df.groupby('Item ID')['Final Inventory'].shift(1)
        y_df.loc[y_df['Initial Inventory'].isna(), 'Initial Inventory'] = y_df.loc[
            y_df['Initial Inventory'].isna(), 'Item ID'
        ].map(dat_in.oi)
        
        flow_warehouse_df = all_items_periods_df.merge(y_df, on=['Item ID', 'Period ID'], how='left')
        flow_warehouse_df = flow_warehouse_df.merge(
            shipments_df[['Item ID', 'Period ID', 'Transferred Qty.']], on=['Item ID', 'Period ID'], how='left'
        )
        flow_warehouse_df['Transferred Qty.'] = flow_warehouse_df['Transferred Qty.'].fillna(0)
        flow_warehouse_df = flow_warehouse_df.rename(columns={'Transferred Qty.': 'Received Qty.'})
        flow_warehouse_df = flow_warehouse_df.merge(
            dat.demand[['Item ID', 'Period ID', 'Demand Qty.', 'Min Inventory']],
            on=['Item ID', 'Period ID'],
            how='left'
        )
        flow_warehouse_df['Demand Qty.'] = flow_warehouse_df['Demand Qty.'].fillna(0)
        flow_warehouse_df['Min Inventory'] = flow_warehouse_df['Min Inventory'].fillna(0)
        flow_warehouse_df = flow_warehouse_df.merge(
            inventory_df_warehouse[['Item ID', 'Unit Holding Cost']], on='Item ID', how='left'
        )
        flow_warehouse_df['Holding Cost'] = flow_warehouse_df['Final Inventory'] * flow_warehouse_df['Unit Holding Cost']
        flow_warehouse_df = flow_warehouse_df.astype({
            'Item ID': str, 'Period ID': int, 'Initial Inventory': float, 'Received Qty.': float,
            'Demand Qty.': float, 'Final Inventory': float, 'Min Inventory': float, 'Unit Holding Cost': float,
            'Holding Cost': float
        })
        self.flow_warehouse_df = flow_warehouse_df

        # create total_inventory dataframe
        inventory_capacity_supplier_df = pd.DataFrame(
            data=itertools.product(dat_in.suppliers_ids, T), columns=['Site ID', 'Period ID']
        )
        inventory_capacity_supplier_df['Inventory Capacity'] = inventory_capacity_supplier_df['Period ID'].map(dat_in.ius)
        inventory_capacity_warehouse_df = pd.DataFrame({
            'Site ID': list(dat_in.warehouses_ids) * len(T),
            'Period ID': T * len(dat_in.warehouses_ids)
        })
        inventory_capacity_warehouse_df['Inventory Capacity'] = inventory_capacity_supplier_df['Period ID'].map(dat_in.iu)
        
        total_inventory_df_supplier = flow_supplier_df.groupby('Period ID')['Final Inventory'].agg('sum').reset_index()
        total_inventory_df_supplier = total_inventory_df_supplier.merge(
            inventory_capacity_supplier_df[['Site ID', 'Period ID', 'Inventory Capacity']], on='Period ID'
        )
        total_inventory_df_warehouse = flow_warehouse_df.groupby('Period ID')['Final Inventory'].agg('sum').reset_index()
        total_inventory_df_warehouse = total_inventory_df_warehouse.merge(
            inventory_capacity_warehouse_df[['Site ID', 'Period ID', 'Inventory Capacity']], on='Period ID'
        )
        total_inventory_df = pd.concat([total_inventory_df_supplier, total_inventory_df_warehouse], ignore_index=True)
        total_inventory_df = total_inventory_df.astype({
            'Site ID': str, 'Period ID': int, 'Final Inventory': float, 'Inventory Capacity': float
        })
        total_inventory_df = total_inventory_df.sort_values(by=['Site ID', 'Period ID']).reset_index(drop=True)
        self.total_inventory_df = total_inventory_df

        # create kpis dataframe
        kpis_df = pd.DataFrame(data=kpis_sol, columns=['KPI', 'Value']).astype({'KPI': str, 'Value': float})
        self.kpis_df = kpis_df

    def build_output(self) -> output_schema.PanDat:
        """
        Populates the output "sln" object.

        Returns
        -------
        sln : output_schema.PanDat
            A PanDat object from ticdat package, accordingly to the schemas.output_schema, that contains all output
            tables as attributes.
        """
        print('Building output dat...')
        sln = output_schema.PanDat()
        sln.flow_supplier = self.flow_supplier_df
        sln.flow_warehouse = self.flow_warehouse_df
        sln.orders = self.orders_df
        sln.shipments = self.shipments_df
        sln.total_inventory = self.total_inventory_df
        sln.kpis = self.kpis_df
        return sln
