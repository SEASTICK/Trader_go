"""Independent isolated linear-margin equation for verification, not order execution.

M + q*(mark-entry) - costs - funding = abs(q)*mark*maintenance_rate.
Fixed maintenance rate only; this does not reproduce exchange risk tiers/fees.
"""
import math

def liquidation_threshold(entry, quantity, collateral, costs=0., funding=0., maintenance_rate=.005):
    values=(entry,quantity,collateral,costs,funding,maintenance_rate)
    if (not all(math.isfinite(v) for v in values) or entry<=0 or quantity==0
            or collateral<=0 or costs<0 or not 0<=maintenance_rate<1):
        raise ValueError('Invalid isolated-margin inputs')
    value=(quantity*entry-collateral+costs+funding)/(quantity-abs(quantity)*maintenance_rate)
    return max(0.,value)
