"""
Contains the class that builds and solves the optimization model.
"""

import pulp as plp
import time
import itertools


class OptModel:
    """
    Builds and solves the optimization model.
    """

    def __init__(self, dat_in, model_name: str) -> None:
        """
        Initializes the optimization model and placeholders for future useful data.

        It receives the dat_in parameter, which must be a DatIn instance, containing all the input data properly
        organized to feed the optimization model.

        Parameters
        ----------
        dat_in : DatIn
            A DatIn instance containing the input data (see data_bridge.py).
        model_name : str
            A name for the optimization model.
        """
        # read input parameters
        self.model_name = model_name
        self.dat_in = dat_in

        # initialize (PuLP) optimization model
        self.mdl = plp.LpProblem(model_name, plp.LpMinimize)

        # initialize placeholders
        self.sol = None
        self.vars = {}
        self.inventory_cost_s = None  # will be created inside _build_objective()
        self.inventory_cost = None  # will be created inside _build_objective()
        self.purchase_cost = None  # will be created inside _build_objective()
        self.total_cost = None  # will be created inside _build_objective()

    def build_base_model(self) -> None:
        """
        Build the base optimization model.
        """
        # Define the model
        print('Building base optimization model...')
        self._add_decision_variables()
        self._add_base_constraints()
        self._build_objective()

        # Variável de decisão para monitorar o número de tipos de itens diferentes recebidos por semana
        self._add_received_items_variables()

        # Restrição de limite de recebimento
        self._add_received_items_limit_constraint()

        # Penalidade no objetivo
        self._add_penalty_to_objective()

    def _add_decision_variables(self) -> None:
        """Add the decision variables."""
        mdl, dat_in = self.mdl, self.dat_in
        x_keys, y_keys, z_keys, ys_keys = dat_in.x_keys, dat_in.y_keys, dat_in.z_keys, dat_in.ys_keys
        w_keys, zs_keys = dat_in.w_keys, dat_in.zs_keys

        t1 = time.perf_counter()
        # create decision variables (add to mdl)
        x = plp.LpVariable.dicts('x', x_keys, lowBound=0, cat=plp.LpContinuous)  # Order qty
        y = plp.LpVariable.dicts('y', y_keys, lowBound=0, cat=plp.LpContinuous)  # Inventory
        z = plp.LpVariable.dicts('z', z_keys, cat=plp.LpBinary)  # Order
        ys = plp.LpVariable.dicts('ys', ys_keys, lowBound=0, cat=plp.LpContinuous)  # S inventory
        w = plp.LpVariable.dicts('w', w_keys, lowBound=0, cat=plp.LpContinuous)  # Transfer qty
        zs = plp.LpVariable.dicts('zs', zs_keys, cat=plp.LpBinary)  # Transfer

        self.vars['x'] = x
        self.vars['y'] = y
        self.vars['z'] = z
        self.vars['ys'] = ys
        self.vars['w'] = w
        self.vars['zs'] = zs
        t2 = time.perf_counter()
        print(f"ADDING DECISION VARS: {t2 - t1:.4f} s")

    def _add_base_constraints(self) -> None:
        """Add the constraints"""
        mdl, dat_in = self.mdl, self.dat_in
        x, y, z = self.vars['x'], self.vars['y'], self.vars['z']
        ys, w, zs = self.vars['ys'], self.vars['w'], self.vars['zs']

        x_keys, y_keys, z_keys, ys_keys = dat_in.x_keys, dat_in.y_keys, dat_in.z_keys, dat_in.ys_keys
        w_keys, zs_keys = dat_in.w_keys, dat_in.zs_keys

        I, T = dat_in.I, dat_in.T
        t0 = dat_in.t0
        ois, oi, il, iu, ius = dat_in.ois, dat_in.oi, dat_in.il, dat_in.iu, dat_in.ius
        d, moq, maxoq, mtq = dat_in.d, dat_in.moq, dat_in.maxoq, dat_in.mtq
        tu, ec, rc = dat_in.tu, dat_in.ec, dat_in.rc

        t00 = time.perf_counter()
        # C0) Initial inventories:
        for i in I:
            mdl.addConstraint(ys[i, t0 - 1] == ois.get(i, 0), name=f'C0a_{i}')
            mdl.addConstraint(y[i, t0 - 1] == oi.get(i, 0), name=f'C0b_{i}')

        t1 = time.perf_counter()
        print(f"ADDING C0: {t1 - t00:.4f} s")
        # C1) Flow balance at the supplier:
        for i, t in itertools.product(I, T):
            mdl.addConstraint(ys[i, t - 1] + x[i, t] == w[i, t] + ys[i, t], name=f'C1_{i}_{t}')

        t2 = time.perf_counter()
        print(f"ADDING C1: {t2 - t1:.4f} s")
        # C2) Flow balance at the warehouse:
        for i, t in itertools.product(I, T):
            mdl.addConstraint(y[i, t - 1] + w[i, t] == d.get((i, t), 0) + y[i, t], name=f'C2_{i}_{t}')

        t3 = time.perf_counter()
        print(f"ADDING C2: {t3 - t2:.4f} s")
        # C3) Minimum and maximum order quantities:
        for i, t in itertools.product(I, T):
            mdl.addConstraint(moq[i] * z[i, t] <= x[i, t], name=f'C3a_{i}_{t}')
            mdl.addConstraint(x[i, t] <= maxoq[i] * z[i, t], name=f'C3b_{i}_{t}')

        t4 = time.perf_counter()
        print(f"ADDING C3: {t4 - t3:.4f} s")
        # C4) Minimum inventory quantity at the warehouse:
        for i, t in il:
            mdl.addConstraint(il[i, t] <= y[i, t], name=f'C4_{i}_{t}')

        t5 = time.perf_counter()
        print(f"ADDING C4: {t5 - t4:.4f} s")
        # C5) Inventory capacity:
        for t in T:
            mdl.addConstraint(plp.lpSum(y.get((i, t), 0) for i in I) <= iu[t], name=f'C5a_{t}')
            mdl.addConstraint(plp.lpSum(ys.get((i, t), 0) for i in I) <= ius[t], name=f'C5b_{t}')

        t6 = time.perf_counter()
        print(f"ADDING C5: {t6 - t5:.4f} s")
        # C6) Minimum transfer size:
        for i, t in itertools.product(I, T):
            mdl.addConstraint(mtq[i] * zs[i, t] <= w[i, t], name=f'C6a_{i}_{t}')
            mdl.addConstraint(w[i, t] <= ec * zs[i, t], name=f'C6b_{i}_{t}')

        t6 = time.perf_counter()
        print(f"ADDING C6: {t6 - t5:.4f} s")
        # C7) Expedition capacity:
        for t in T:
            mdl.addConstraint(plp.lpSum(w.get((i, t), 0) for i in I) <= ec, name=f'C7_{t}')

        t7 = time.perf_counter()
        print(f"ADDING C7: {t7 - t6:.4f} s")
        # C8) Receiving capacity:
        for t in T:
            mdl.addConstraint(plp.lpSum(zs.get((i, t), 0) for i in I) <= rc, name=f'C8_{t}')

        t8 = time.perf_counter()
        print(f"ADDING C8: {t8 - t7:.4f} s")
        # C9) Max inventory aging:
        for t in range(t0 - 1, max(T) - tu + 1):
            for i in I:
                mdl.addConstraint(ys[i, t] <= plp.lpSum(w[i, tp] for tp in range(t + 1, t + tu + 1)), name=f'C9_{i}_{t}')

        t9 = time.perf_counter()
        print(f"ADDING C9: {t9 - t8:.4f} s")

    def _build_objective(self) -> None:
        """
        Build and set the objective function.
        """
        mdl, dat_in = self.mdl, self.dat_in
        x, y, ys = self.vars['x'], self.vars['y'], self.vars['ys']
        pc, ci, cis = dat_in.pc, dat_in.ci, dat_in.cis

        # Objective function
        self.inventory_cost_s = plp.lpSum(cis[i] * ys[i, t] for i, t in ys)
        self.inventory_cost = plp.lpSum(ci[i] * y[i, t] for i, t in y)
        self.purchase_cost = plp.lpSum(pc[i, t] * x[i, t] for i, t in x)
        self.total_cost = self.purchase_cost + self.inventory_cost + self.inventory_cost_s
        mdl.setObjective(self.total_cost)

    def _add_received_items_variables(self) -> None:
        """Variáveis de decisão para monitorar o número de tipos de itens diferentes recebidos por semana"""
        mdl, dat_in = self.mdl, self.dat_in
        T = dat_in.T
        num_items_received = plp.LpVariable.dicts('num_items_received', T, lowBound=0, upBound=30, cat=plp.LpInteger)
        self.vars['num_items_received'] = num_items_received

    def _add_received_items_limit_constraint(self) -> None:
        """Restrição que impõe um limite de 30 tipos de itens recebidos por semana"""
        mdl, dat_in = self.mdl, self.dat_in
        T = dat_in.T
        num_items_received = self.vars['num_items_received']

        for t in T:
            mdl.addConstraint(num_items_received[t] <= 30, name=f'ReceivedItemsLimit_{t}')

    def _add_penalty_to_objective(self) -> None:
        """Penalidade no objetivo caso mais de 4 itens diferentes sejam recebidos"""
        mdl, dat_in = self.mdl, self.dat_in
        penalty_cost = plp.LpVariable('penalty_cost', lowBound=0, cat=plp.LpContinuous)
        self.vars['penalty_cost'] = penalty_cost

        # Adicionar a penalidade no custo total
        mdl.setObjective(self.total_cost + penalty_cost)

        # Adicionar a restrição para ativar a penalidade caso mais de 4 itens diferentes sejam recebidos
        num_items_received = self.vars['num_items_received']
        mdl.addConstraint(penalty_cost >= 10000 * (plp.lpSum(num_items_received[t] for t in num_items_received) - 4), name='PenaltyConstraint')
    
    def add_complexity_8(self) -> None:
        """
        Do not allow high stock cost
        """

        # previous parameters and variables
        mdl = self.mdl
        ci, cis = self.dat_in.ci, self.dat_in.cis
        y, ys = self.vars['y'], self.vars['ys']

        # add new constraint:
        # maximum inventory cost for supplier is 12000
        mdl.addConstraint(plp.lpSum(cis[i] * ys[i, t] for i, t in ys) <= 10000, name=f'C19')
        # maximum inventory cost for warehouse is  200000
        mdl.addConstraint(plp.lpSum(ci[i] * y[i, t] for i, t in y) <= 210000, name=f'C20')

    def optimize(self) -> None:
        """
        Calls the optimizer, and populates the solution data (if any).
        """
        print('Solving the optimization model...')
        mdl = self.mdl

        mdl.solve(plp.PULP_CBC_CMD(timeLimit=10*60, gapRel=0.01))

        # print status
        status = plp.LpStatus[mdl.status]
        print(f"Model status: {status}")

        # build solution
        if mdl.status in [plp.LpStatusOptimal]:
            x, y, z = self.vars['x'], self.vars['y'], self.vars['z']
            ys, w, zs = self.vars['ys'], self.vars['w'], self.vars['zs']
            x_sol = {key: var.varValue for key, var in x.items() if var.varValue > 1e-2}
            y_sol = {key: var.varValue for key, var in y.items()}
            z_sol = [key for key, var in z.items() if var.varValue > 1e-2]
            ys_sol = {key: var.varValue for key, var in ys.items()}
            w_sol = {key: var.varValue for key, var in w.items() if var.varValue > 1e-2}
            zs_sol = [key for key, var in zs.items() if var.varValue > 1e-2]

            kpis_sol = [
                ('Total Cost', plp.value(self.total_cost)),
                ('Total Procurement Cost', plp.value(self.purchase_cost)),
                ('Total Inventory Holding Cost (supplier)', plp.value(self.inventory_cost_s)),
                ('Total Inventory Holding Cost (warehouse)', plp.value(self.inventory_cost)),
            ]

            self.sol = {
                'status': mdl.status,
                'obj_val': plp.value(mdl.objective),
                'vars': {'x': x_sol, 'y': y_sol, 'z': z_sol, 'ys': ys_sol, 'w': w_sol, 'zs': zs_sol, 'kpis': kpis_sol}
            }

        else:
            self.sol = {'status': mdl.status}
