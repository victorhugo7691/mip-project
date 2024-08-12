import inspect
import os
from ticdat import PanDatFactory
from ticdat import TicDatFactory


def _this_directory():
    return os.path.dirname(os.path.realpath(os.path.abspath(inspect.getsourcefile(_this_directory))))


def read_data(input_data_loc, schema):
    """
    Reads data from files and populates an instance of the corresponding schema.

    Parameters
    ----------
    input_data_loc: str
        The location of the data set inside the `data/` directory.
        It can be a directory containing CSV files, a xls/xlsx file, or a json file.
    schema: PanDatFactory
        An instance of the PanDatFactory class of ticdat.
    Returns
    -------
    PanDat
        a PanDat object populated with the tables available in the input_data_loc.
    """
    print(f'Reading data from: {input_data_loc}')
    path = os.path.join(_this_directory(), "data", input_data_loc)
    assert os.path.exists(path), f"bad path {path}"
    if input_data_loc.endswith(".xlsx") or input_data_loc.endswith(".xls"):
        dat = schema.xls.create_pan_dat(path)
    elif input_data_loc.endswith("json"):
        dat = schema.json.create_pan_dat(path)
    else:  # read from cvs files
        dat = schema.csv.create_pan_dat(path)
    return dat


def write_data(sln, output_data_loc, schema):
    """
    Writes data to the specified location.

    Parameters
    ----------
    sln: PanDat
        A PanDat object populated with the data to be written to file/files.
    output_data_loc: str
        A destination inside `data/` to write the data to.
        It can be a directory (to save the data as CSV files), a xls/xlsx file, or a json file.
    schema: PanDatFactory
        An instance of the PanDatFactory class of ticdat compatible with sln.
    Returns
    -------
    None
    """
    print(f'Writing data back to: {output_data_loc}')
    path = os.path.join(_this_directory(), "data", output_data_loc)
    # assert os.path.exists(path), f"bad path {path}"
    if output_data_loc.endswith(".xlsx") or output_data_loc.endswith("xls"):
        schema.xls.write_file(sln, path)
    elif output_data_loc.endswith(".json"):
        schema.json.write_file_pd(sln, path, orient='split')
    else:  # write to csv files
        schema.csv.write_directory(sln, path)
    return None


def print_failures(schema, failures):
    """Prints out a sample of the data failure encountered."""
    if isinstance(schema, PanDatFactory):
        for table_name, table in failures.items():
            print(table_name)
            print(table.head().to_string())
    elif isinstance(schema, TicDatFactory):
        for table_name, table in failures.items():
            print(table_name)
            print({key: table[key] for key in list(table)[:5]})
    else:
        raise ValueError('bad schema')


def check_data(dat, schema):
    """
    Runs data integrity checks and prints out some sample failures to facilitate debugging.

    :param dat: A PanDat or TicDat object.
    :param schema: The schema that `dat` belongs to.
    :return: None
    """
    print('Running data integrity check...')
    assert isinstance(schema, (TicDatFactory, PanDatFactory))
    if isinstance(schema, TicDatFactory):
        if not schema.good_tic_dat_object(dat):
            raise AssertionError("Not a good TicDat object")
    else:
        if not schema.good_pan_dat_object(dat):
            raise AssertionError("Not a good PanDat object")
    foreign_key_failures = schema.find_foreign_key_failures(dat)
    if foreign_key_failures:
        print_failures(schema, foreign_key_failures)
        raise AssertionError(f"Foreign key failures found in {len(foreign_key_failures)} table(s)/field(s).")
    data_type_failures = schema.find_data_type_failures(dat)
    if data_type_failures:
        print_failures(schema, data_type_failures)
        raise AssertionError(f"Data type failures found in {len(data_type_failures)} table(s)/field(s).")
    data_row_failures = schema.find_data_row_failures(dat)
    if data_row_failures:
        print_failures(schema, data_row_failures)
        raise AssertionError(f"Data row failures found in {len(data_row_failures)} table(s)/field(s).")
    duplicates = schema.find_duplicates(dat)
    if duplicates:
        print_failures(schema, duplicates)
        raise AssertionError(f"Duplicates found in {len(duplicates)} table(s)/field(s).")
    print('Data is good!')
