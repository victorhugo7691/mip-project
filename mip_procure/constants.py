from collections import namedtuple


# Constants for Site Type
_SiteTypes = namedtuple(
    'SiteTypes', ['WAREHOUSE', 'SUPPLIER']
)
SiteTypes = _SiteTypes(
    WAREHOUSE='Warehouse',
    SUPPLIER='Supplier'
)
