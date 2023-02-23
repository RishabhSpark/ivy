# global
import paddle
from typing import Optional

# local
import ivy

from . import backend_version
from ivy.utils.exceptions import IvyNotImplementedException


def argsort(
    x: paddle.Tensor,
    /,
    *,
    axis: int = -1,
    descending: bool = False,
    stable: bool = True,
    out: Optional[paddle.Tensor] = None,
) -> paddle.Tensor:
    if ivy.as_native_dtype(x.dtype) == paddle.bool:
        x = x.cast('int32')
    return paddle.argsort(x, axis=axis , descending=descending)


def sort(
    x: paddle.Tensor,
    /,
    *,
    axis: int = -1,
    descending: bool = False,
    stable: bool = True,
    out: Optional[paddle.Tensor] = None,
) -> paddle.Tensor:
    
    is_bool = ivy.as_native_dtype(x.dtype) == paddle.bool
    if is_bool:
        x = x.cast('int32')

    ret = paddle.sort(x, axis=axis , descending=descending)
    
    if is_bool:
        ret = ret.cast('bool')
    
    return ret


def searchsorted(
    x: paddle.Tensor,
    v: paddle.Tensor,
    /,
    *,
    side="left",
    sorter=None,
    ret_dtype=paddle.int64,
    out: Optional[paddle.Tensor] = None,
) -> paddle.Tensor:
    raise IvyNotImplementedException()
