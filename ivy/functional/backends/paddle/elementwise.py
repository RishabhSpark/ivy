# global
from typing import Union, Optional

import paddle

# local
import ivy
from . import backend_version
from ivy.utils.exceptions import IvyNotImplementedException


def add(
    x1: Union[float, paddle.Tensor],
    x2: Union[float, paddle.Tensor],
    /,
    *,
    alpha: Optional[Union[int, float]] = None,
    out: Optional[paddle.Tensor] = None,
) -> paddle.Tensor:
    x1, x2 = ivy.promote_types_of_inputs(x1, x2)
    if alpha not in (1, None):
        x2 = multiply(x2, alpha)
    return paddle.add(x1, x2)

def bitwise_xor(
    x1: Union[int, bool, paddle.Tensor],
    x2: Union[int, bool, paddle.Tensor],
    /,
    *,
    out: Optional[paddle.Tensor] = None,
) -> paddle.Tensor:
    raise IvyNotImplementedException()


def expm1(x: paddle.Tensor, /, *, out: Optional[paddle.Tensor] = None) -> paddle.Tensor:
    raise IvyNotImplementedException()


def bitwise_invert(
    x: Union[int, bool, paddle.Tensor], /, *, out: Optional[paddle.Tensor] = None
) -> paddle.Tensor:
    return paddle.bitwise_not(x)


def isfinite(x: paddle.Tensor, /, *, out: Optional[paddle.Tensor] = None) -> paddle.Tensor:
    raise IvyNotImplementedException()


def isinf(
    x: paddle.Tensor,
    /,
    *,
    detect_positive: bool = True,
    detect_negative: bool = True,
    out: Optional[paddle.Tensor] = None,
) -> paddle.Tensor:
    raise IvyNotImplementedException()


def equal(
    x1: Union[float, paddle.Tensor],
    x2: Union[float, paddle.Tensor],
    /,
    *,
    out: Optional[paddle.Tensor] = None,
) -> paddle.Tensor:
    raise IvyNotImplementedException()


def less_equal(
    x1: Union[float, paddle.Tensor],
    x2: Union[float, paddle.Tensor],
    /,
    *,
    out: Optional[paddle.Tensor] = None,
) -> paddle.Tensor:
    raise IvyNotImplementedException()


def bitwise_and(
    x1: Union[int, bool, paddle.Tensor],
    x2: Union[int, bool, paddle.Tensor],
    /,
    *,
    out: Optional[paddle.Tensor] = None,
) -> paddle.Tensor:
    raise IvyNotImplementedException()


def ceil(x: paddle.Tensor, /, *, out: Optional[paddle.Tensor] = None) -> paddle.Tensor:
    raise IvyNotImplementedException()


def floor(x: paddle.Tensor, /, *, out: Optional[paddle.Tensor] = None) -> paddle.Tensor:
    raise IvyNotImplementedException()


def asin(x: paddle.Tensor, /, *, out: Optional[paddle.Tensor] = None) -> paddle.Tensor:
    return asin(x)


def asinh(x: paddle.Tensor, /, *, out: Optional[paddle.Tensor] = None) -> paddle.Tensor:
    return paddle.asinh(x)


def sign(x: paddle.Tensor, /, *, out: Optional[paddle.Tensor] = None) -> paddle.Tensor:
    raise IvyNotImplementedException()


def sqrt(x: paddle.Tensor, /, *, out: Optional[paddle.Tensor] = None) -> paddle.Tensor:
    raise IvyNotImplementedException()


def cosh(x: paddle.Tensor, /, *, out: Optional[paddle.Tensor] = None) -> paddle.Tensor:
    return paddle.cosh(x)


def log10(x: paddle.Tensor, /, *, out: Optional[paddle.Tensor] = None) -> paddle.Tensor:
    raise IvyNotImplementedException()


def log2(x: paddle.Tensor, /, *, out: Optional[paddle.Tensor] = None) -> paddle.Tensor:
    raise IvyNotImplementedException()


def log1p(x: paddle.Tensor, /, *, out: Optional[paddle.Tensor] = None) -> paddle.Tensor:
    raise IvyNotImplementedException()


def isnan(x: paddle.Tensor, /, *, out: Optional[paddle.Tensor] = None) -> paddle.Tensor:
    raise IvyNotImplementedException()


def less(
    x1: Union[float, paddle.Tensor],
    x2: Union[float, paddle.Tensor],
    /,
    *,
    out: Optional[paddle.Tensor] = None,
) -> paddle.Tensor:
    raise IvyNotImplementedException()


def multiply(
    x1: Union[float, paddle.Tensor],
    x2: Union[float, paddle.Tensor],
    /,
    *,
    out: Optional[paddle.Tensor] = None,
) -> paddle.Tensor:
    raise IvyNotImplementedException()


def cos(x: paddle.Tensor, /, *, out: Optional[paddle.Tensor] = None) -> paddle.Tensor:
    return paddle.cos(x)


def logical_not(
    x: paddle.Tensor, /, *, out: Optional[paddle.Tensor] = None
) -> paddle.Tensor:
    raise IvyNotImplementedException()


def divide(
    x1: Union[float, paddle.Tensor],
    x2: Union[float, paddle.Tensor],
    /,
    *,
    out: Optional[paddle.Tensor] = None,
) -> paddle.Tensor:
    raise IvyNotImplementedException()


def greater(
    x1: Union[float, paddle.Tensor],
    x2: Union[float, paddle.Tensor],
    /,
    *,
    out: Optional[paddle.Tensor] = None,
) -> paddle.Tensor:
    raise IvyNotImplementedException()


def greater_equal(
    x1: Union[float, paddle.Tensor],
    x2: Union[float, paddle.Tensor],
    /,
    *,
    out: Optional[paddle.Tensor] = None,
) -> paddle.Tensor:
    raise IvyNotImplementedException()


def acos(x: paddle.Tensor, /, *, out: Optional[paddle.Tensor] = None) -> paddle.Tensor:
    return paddle.acos(x)


def logical_xor(
    x1: paddle.Tensor, x2: paddle.Tensor, /, *, out: Optional[paddle.Tensor] = None
) -> paddle.Tensor:
    raise IvyNotImplementedException()


def logical_and(
    x1: paddle.Tensor, x2: paddle.Tensor, /, *, out: Optional[paddle.Tensor] = None
) -> paddle.Tensor:
    raise IvyNotImplementedException()


def logical_or(
    x1: paddle.Tensor, x2: paddle.Tensor, /, *, out: Optional[paddle.Tensor] = None
) -> paddle.Tensor:
    raise IvyNotImplementedException()


def acosh(x: paddle.Tensor, /, *, out: Optional[paddle.Tensor] = None) -> paddle.Tensor:
    return paddle.acosh(x)


def sin(x: paddle.Tensor, /, *, out: Optional[paddle.Tensor] = None) -> paddle.Tensor:
    return paddle.sin(x)


def negative(
    x: Union[float, paddle.Tensor], /, *, out: Optional[paddle.Tensor] = None
) -> paddle.Tensor:
    raise IvyNotImplementedException()


def not_equal(
    x1: Union[float, paddle.Tensor],
    x2: Union[float, paddle.Tensor],
    /,
    *,
    out: Optional[paddle.Tensor] = None,
) -> paddle.Tensor:
    raise IvyNotImplementedException()


def tanh(x: paddle.Tensor, /, *, out: Optional[paddle.Tensor] = None) -> paddle.Tensor:
    return paddle.tanh(x)


def floor_divide(
    x1: Union[float, paddle.Tensor],
    x2: Union[float, paddle.Tensor],
    /,
    *,
    out: Optional[paddle.Tensor] = None,
) -> paddle.Tensor:
    raise IvyNotImplementedException()


def bitwise_or(
    x1: Union[int, bool, paddle.Tensor],
    x2: Union[int, bool, paddle.Tensor],
    /,
    *,
    out: Optional[paddle.Tensor] = None,
) -> paddle.Tensor:
    raise IvyNotImplementedException()


def sinh(x: paddle.Tensor, /, *, out: Optional[paddle.Tensor] = None) -> paddle.Tensor:
    return paddle.sinh(x)


def positive(
    x: Union[float, paddle.Tensor], /, *, out: Optional[paddle.Tensor] = None
) -> paddle.Tensor:
    raise IvyNotImplementedException()


def square(x: paddle.Tensor, /, *, out: Optional[paddle.Tensor] = None) -> paddle.Tensor:
    raise IvyNotImplementedException()


def pow(
    x1: Union[float, paddle.Tensor],
    x2: Union[float, paddle.Tensor],
    /,
    *,
    out: Optional[paddle.Tensor] = None,
) -> paddle.Tensor:
    raise IvyNotImplementedException()


def round(x: paddle.Tensor, /, *, out: Optional[paddle.Tensor] = None) -> paddle.Tensor:
    raise IvyNotImplementedException()


def trunc(x: paddle.Tensor, /, *, out: Optional[paddle.Tensor] = None) -> paddle.Tensor:
    raise IvyNotImplementedException()


def abs(
    x: Union[float, paddle.Tensor], /, *, out: Optional[paddle.Tensor] = None
) -> paddle.Tensor:
    raise IvyNotImplementedException()


def logaddexp(
    x1: paddle.Tensor, x2: paddle.Tensor, /, *, out: Optional[paddle.Tensor] = None
) -> paddle.Tensor:
    raise IvyNotImplementedException()


def tan(x: paddle.Tensor, /, *, out: Optional[paddle.Tensor] = None) -> paddle.Tensor:
    return paddle.tan(x)


def atan(x: paddle.Tensor, /, *, out: Optional[paddle.Tensor] = None) -> paddle.Tensor:
    return paddle.atan(x)

  # TODO Fixed in PyTorch 1.12.1 (this note excludes complex)


def atan2(
    x1: paddle.Tensor, x2: paddle.Tensor, /, *, out: Optional[paddle.Tensor] = None
) -> paddle.Tensor:
    raise IvyNotImplementedException()


def log(x: paddle.Tensor, /, *, out: Optional[paddle.Tensor] = None) -> paddle.Tensor:
    return paddle.log(x)


def exp(x: paddle.Tensor, /, *, out: Optional[paddle.Tensor] = None) -> paddle.Tensor:
    raise IvyNotImplementedException()


def subtract(
    x1: Union[float, paddle.Tensor],
    x2: Union[float, paddle.Tensor],
    /,
    *,
    alpha: Optional[Union[int, float]] = None,
    out: Optional[paddle.Tensor] = None,
) -> paddle.Tensor:
    x1, x2 = ivy.promote_types_of_inputs(x1, x2)
    if alpha not in (1, None):
        x2 = multiply(x2, alpha)
    return paddle.subtract(x1,x2)


def remainder(
    x1: Union[float, paddle.Tensor],
    x2: Union[float, paddle.Tensor],
    /,
    *,
    modulus: bool = True,
    out: Optional[paddle.Tensor] = None,
) -> paddle.Tensor:
    raise IvyNotImplementedException()


def atanh(x: paddle.Tensor, /, *, out: Optional[paddle.Tensor] = None) -> paddle.Tensor:
    return paddle.atanh(x)


def bitwise_right_shift(
    x1: Union[int, bool, paddle.Tensor],
    x2: Union[int, bool, paddle.Tensor],
    /,
    *,
    out: Optional[paddle.Tensor] = None,
) -> paddle.Tensor:
    raise IvyNotImplementedException()


def bitwise_left_shift(
    x1: Union[int, bool, paddle.Tensor],
    x2: Union[int, bool, paddle.Tensor],
    /,
    *,
    out: Optional[paddle.Tensor] = None,
) -> paddle.Tensor:
    raise IvyNotImplementedException()


# Extra #
# ------#


def erf(x: paddle.Tensor, /, *, out: Optional[paddle.Tensor] = None) -> paddle.Tensor:
    raise IvyNotImplementedException()


def minimum(
    x1: Union[float, paddle.Tensor],
    x2: Union[float, paddle.Tensor],
    /,
    *,
    use_where: bool = True,
    out: Optional[paddle.Tensor] = None,
) -> paddle.Tensor:
    raise IvyNotImplementedException()


def maximum(
    x1: Union[float, paddle.Tensor],
    x2: Union[float, paddle.Tensor],
    /,
    *,
    use_where: bool = True,
    out: Optional[paddle.Tensor] = None,
) -> paddle.Tensor:
    raise IvyNotImplementedException()


def reciprocal(
    x: Union[float, paddle.Tensor], /, *, out: Optional[paddle.Tensor] = None
) -> paddle.Tensor:
    raise IvyNotImplementedException()


def deg2rad(x: paddle.Tensor, /, *, out: Optional[paddle.Tensor] = None) -> paddle.Tensor:
    return paddle.deg2rad(x)


def rad2deg(x: paddle.Tensor, /, *, out: Optional[paddle.Tensor] = None) -> paddle.Tensor:
    raise IvyNotImplementedException()


def trunc_divide(
    x1: Union[float, paddle.Tensor],
    x2: Union[float, paddle.Tensor],
    /,
    *,
    out: Optional[paddle.Tensor] = None,
) -> paddle.Tensor:
    raise IvyNotImplementedException()


def isreal(x: paddle.Tensor, /, *, out: Optional[paddle.Tensor] = None) -> paddle.Tensor:
    raise IvyNotImplementedException()
