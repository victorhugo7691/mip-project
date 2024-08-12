# Remarks about the project

## Additional Complexities

- **Lead time**: include a transportation time between the supplier and the warehouse. It can be a deterministic lead time, for instance. The input spreadsheet `Template2.xls` mentions `Lead Time (weeks)` in the table `Item Mapping and Pricing`. In this case, we would probably need a high initial inventory at the warehouse (or loads already moving to the warehouse) in order to satisfy the demands for early periods, otherwise the model will be infeasible.
- **Multiple suppliers/warehouses**.
- Consider the "**Cummulative Discount**" in the price tiers modeling, instead of the "All-Units Discount".
- **Transfer Time** of items from suppliers to warehouses. If so, how to charge for shipments? Unit price, or trucks prices given their capacities?

## Questions

- Should we add a **slack variable** (to be minimized) for the demand in the warehouse flow balance? Just to avoid possible infeasibility issues.
- Should we mention the **Production forecast** input tab (see `Template2.xls`) in the input schema? As far as I understood, what matters is only the `Bag Demand`, which is calculated from the `Production forecast` (for each size of packed pet food, I suppose) and the sizes of bags (in `Item Mapping and Pricing` at `Unit weight (lbs)` column).
- How to model the price tiers and breakpoints in a generic way such that we can easily change from All-Units discount to Cumulative discount and vice-versa? For instance, Cumulative discount requires the end of a tier to match the start of the next tier, while for the All-Units discount we could allow the user to leave some unachievable intervals.

## Observations

- ETA is understood as the estimated **period** when the shipment will arrive.

## TODOs

- should columns that refer to items quantities be integer (thinking about bags, for instance)? How to handle different items with different data types? Maybe adding a field to ask whether that item must be integer or not.
