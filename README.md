# Mip Procure

## Repository guide
- [docs](docs): Hosts documentation (in addition to readme files and docstrings)
  of the project.
- [mip_procure](mip_procure): Contains the Python package that solves the 
  problem.
  It contains scripts that define the input and the output data schemas, the 
  solution engine, and other auxiliary modules.
- [test_mip_procure](test_mip_procure): Hosts testing suits and testing data 
  sets used for testing the solution throughout the development process.
- `pyproject.toml` and `setup.cfg` are used to build the distribution files 
  of the package (more information [here](https://github.com/mipwise/mip-go/blob/main/6_deploy/1_distribution_package/README.md)).