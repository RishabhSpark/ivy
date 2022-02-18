# local
from ivy.func_wrapper import _wrap_methods, _unwrap_methods

array_mode_val = False


def set_array_mode(val=True):
    global array_mode_val
    if val:
        if not array_mode_val:
            _wrap_methods()
    elif array_mode_val:
        _unwrap_methods()
    array_mode_val = val


def unset_array_mode():
    global array_mode_val
    array_mode_val = False
    _unwrap_methods()


def array_mode():
    return array_mode_val
