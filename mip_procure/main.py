from mip_procure.data_bridge import DatIn, DatOut
from mip_procure.opt_model import OptModel
from mip_procure.schemas import input_schema, output_schema


def solve(dat: input_schema.PanDat) -> output_schema.PanDat:
    dat_in = DatIn(dat, verbose=True)
    opt_model = OptModel(dat_in, model_name='Mip_Procure')
    opt_model.build_base_model()
    # opt_model.add_complexity_1()
    # opt_model.add_complexity_2_proportional()
    # opt_model.add_complexity_2_fixed()
    # opt_model.add_complexity_3()
    # opt_model.add_complexity_4()
    # opt_model.add_complexity_5()
    # opt_model.add_complexity_6()
    # opt_model.add_complexity_7()
    # opt_model.add_complexity_8()
    opt_model.add_complexity4()
    opt_model.optimize()
    # opt_model.mdl.write('lp.lp')
    dat_out = DatOut(opt_model)
    sln = dat_out.build_output()
    return sln
