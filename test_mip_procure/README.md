# Testing Directory
Besides testing input data, we typically keep two types of files in this 
directory:
- [Local Execution](test_local_execution.py): A module configured to 
  conveniently execute engines in Pycharm or VS Code (even in the debug mode) 
  with one or two clicks. In particular, the methods of the 
  TestLocalExecution class mimics the execution flow on 
  [Mip Hub](https://www.mipwise.com/mip-hub).
- [Test](test_mip_procure.py): Scripts for unit testing.

The [utils.py](utils.py) script contains utility functions to read, write, 
and run data integrity checks locally.
