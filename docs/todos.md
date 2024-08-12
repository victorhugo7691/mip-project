# Notes

- the model implementation (`DatIn` and `OptModel`) are validated, even checked the lp file.
- output tables construction (`DatOut`) was not extensively validated

## TODOs

- valitade a bit more the construction of the output tables (`DatOut`) from what comes out of the optimization solver
- consider implementing the optimization model in `pulp` to assess the same performance the students are going to face
- for Eduardo's students:
    - consider reducing the size of the model (time periods and/or SKUs) to reduce runtime
    - make sure the data instance is feasible
    - try twiking the data (and the optimization model, if necessary) to encourage the solver to keep inventory at the supplier

