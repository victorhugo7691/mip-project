import unittest
from test_mip_procure import utils
import mip_procure


class TestLocalExecution(unittest.TestCase):
    """
    THIS IS NOT UNIT TESTING! Unit testing are implemented in other scripts.

    This class only serves the purpose of conveniently (with one click) executing solve engines locally during
    development.

    In addition, the methods in this class mimic the execution flow that a user typically experience on a Mip Hub app.
    """

    def test_1_action_data_ingestion(self):
        dat = utils.read_data(input_data_loc="testing_data/mip_procure_input_data_v2_small_12_weeks.xlsx",
                              schema=mip_procure.input_schema)
        utils.check_data(dat, mip_procure.input_schema)
        utils.write_data(dat, 'inputs', mip_procure.input_schema)

    def test_2_main_solve(self):
        dat = utils.read_data('inputs', mip_procure.input_schema)
        sln = mip_procure.solve(dat)
        utils.write_data(sln, 'outputs', mip_procure.output_schema)


if __name__ == '__main__':
    unittest.main()
