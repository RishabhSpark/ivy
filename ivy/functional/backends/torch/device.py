"""
Collection of PyTorch general functions, wrapped to fit Ivy syntax and signature.
"""

# global
import os
import importlib
torch_scatter = None
import torch
from typing import Optional
from torch.profiler import ProfilerActivity
from torch.profiler import profile as _profile

# local
import ivy
from ivy.functional.ivy.device import Profiler as BaseProfiler


# API #
# ----#

def dev(x, as_str=False):
    dv = x.device
    if as_str:
        return dev_to_str(dv)
    return dv


def to_dev(x, dev: Optional[str] = None, out: Optional[torch.Tensor] = None) -> torch.Tensor:
    ret = x.to(dev_from_str(dev))
    if isinstance(x, torch.nn.Parameter):
        if ivy.exists(out):
            return ivy.inplace_update(out, torch.nn.Parameter(ret))        
        return torch.nn.Parameter(ret)
    
    if ivy.exists(out):
        return ivy.inplace_update(out, ret)
    return ret


def dev_to_str(dev: torch.device):
    if isinstance(dev, str):
        return dev
    dev_type, dev_idx = (dev.type, dev.index)
    if dev_type == 'cpu':
        return dev_type
    return dev_type.replace('cuda', 'gpu') + (':' + (str(dev_idx) if dev_idx is not None else '0'))


def dev_from_str(dev: Optional[str] = None) -> Optional[torch.device]:
    if not isinstance(dev, str):
        return dev
    return torch.device(dev.replace('gpu', 'cuda'))


def clear_mem_on_dev(dev):
    if 'gpu' in dev:
        torch.cuda.empty_cache()


_callable_dev = dev
gpu_is_available = torch.cuda.is_available
num_gpus = torch.cuda.device_count


# noinspection PyUnresolvedReferences
def tpu_is_available():
    if importlib.util.find_spec("torch_xla") is not None:
        return True
    return False


class Profiler(BaseProfiler):

    def __init__(self, save_dir):
        super(Profiler, self).__init__(save_dir)
        self._prof = _profile(activities=[ProfilerActivity.CPU, ProfilerActivity.CUDA], with_stack=True)

    def start(self):
        self._prof.__enter__()

    def stop(self):
        self._prof.__exit__(None, None, None)
        self._prof.export_chrome_trace(os.path.join(self._save_dir, 'trace.json'))

    def __enter__(self):
        self.start()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
