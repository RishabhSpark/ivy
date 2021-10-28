# global
import ivy
import copy
import queue
import random
import inspect
import importlib
import numpy as np
import networkx as nx
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# local
from ivy.wrapper import _wrap_or_unwrap_methods, NON_WRAPPED_METHODS, ARRAYLESS_RET_METHODS

wrapping_paused = False
op_logging = False
wrapped_stack = list()


ARRAY_BUILTINS = ['__neg__', '__pow__', '__rpow__', '__add__', '__radd__', '__iadd__', '__sub__', '__rsub__',
                  '__isub__', '__mul__', '__rmul__', '__imul__', '__truediv__', '__rtruediv__', '__itruediv__',
                  '__floordiv__', '__rfloordiv__', '__ifloordiv__', '__abs__', '__lt__', '__le__', '__eq__', '__ne__',
                  '__gt__', '__ge__', '__and__', '__rand__', '__or__', '__ror__', '__invert__', '__xor__', '__rxor__',
                  '__getitem__', '__setitem__', '__getattr__', '__setattr__', '__getattribute__']

CLASSES_TO_WRAP = {'numpy': [],
                   'jax': [],
                   'tensorflow': [],
                   'torch': [('torch', 'Tensor')],
                   'mxnet': []}

GRAPH_ATTRIBUTES = {'numpy': [],
                   'jax': [],
                   'tensorflow': [],
                   'torch': ['data', 'requires_grad'],
                   'mxnet': []}


def _get_shape(x_in):
    # noinspection PyBroadException
    try:
        return tuple(x_in.shape)
    except Exception:
        return None


def _args_str_from_fn(fn):
    if hasattr(fn, 'args') and hasattr(fn, 'kwargs'):
        return '\n'.join(
            ['{}: {}'.format(k, v) for k, v in dict(**dict(
                [(str(i), _tensor_to_label(a) if ivy.is_array(a) else a)
                 for i, a in enumerate(fn.args)]), **fn.kwargs).items()])
    else:
        return ''


def _format_label(cls, shape):
    ptype_str = '{}'.format(cls).replace(
        "'", '').replace(' ', '').replace('<', '').replace('>', '').replace('class', '').split('.')[-1]
    if ivy.exists(shape):
        return ptype_str + ', {}'.format(shape)
    return ptype_str


def _tensor_to_label(tnsr):
    return _format_label(type(tnsr), tuple(tnsr.shape))


def _param_to_label(param):
    return _format_label(param.ptype, param.shape)


def _terminal_pids_to_key(terminal_pids):
    return '_'.join([str(pid) for pid in terminal_pids])


class Param:

    def __init__(self, ptype, tree_depth, shape=None):
        self._count = 0
        self._ptype = ptype
        self._tree_depth = tree_depth
        self._param_stack = list()
        self._shape = tuple(shape) if ivy.exists(shape) else None

    def set(self, val):
        self._param_stack = [val]*self._count

    def set_count(self, count):
        self._count = count

    def get(self):
        return self._param_stack.pop()

    def __repr__(self):
        return '<Param, type={}, depth={}, count={}, current={}>'.format(
            self._ptype, self._tree_depth, self._count, len(self._param_stack))

    def __len__(self):
        return len(self._param_stack)

    @property
    def count(self):
        return self._count

    @property
    def depth(self):
        return self._tree_depth

    @property
    def ptype(self):
        return self._ptype

    @property
    def shape(self):
        return self._shape


class Graph:

    # noinspection PyProtectedMember
    def __init__(self, fn, *args, stateful=None, num_workers=1, **kwargs):

        # stateful
        self._stateful = ivy.default(stateful, [])
        self._stateful_classes = tuple([x.__class__ for x in self._stateful])
        self._stateful_param_ids = [id(x) for x in self._stateful]
        self._stateful_param_shapes = [_get_shape(x) for x in self._stateful]

        # function being compiled into a graph
        self._fn = fn

        # positional args
        self._args = list(args)
        self._arg_tracked_idxs = ivy.nested_indices_where(
            args, lambda a: ivy.is_array(a) or isinstance(a, self._stateful_classes))
        self._arg_param_ids = [_get_id(a) for a in ivy.multi_index_nest(args, self._arg_tracked_idxs)]
        self._arg_param_types = [a.__class__ for a in ivy.multi_index_nest(args, self._arg_tracked_idxs)]
        self._arg_param_shapes = [_get_shape(a) for a in ivy.multi_index_nest(args, self._arg_tracked_idxs)]

        # key-word args
        self._kwargs = kwargs
        self._kwarg_tracked_idxs = ivy.nested_indices_where(
            kwargs, lambda v: ivy.is_array(v) or isinstance(v, self._stateful_classes))
        self._kwarg_param_ids = [_get_id(v) for v in ivy.multi_index_nest(kwargs, self._kwarg_tracked_idxs)]
        self._kwarg_param_types = [v.__class__ for v in ivy.multi_index_nest(kwargs, self._kwarg_tracked_idxs)]
        self._kwarg_param_shapes = [_get_shape(a) for a in ivy.multi_index_nest(kwargs, self._kwarg_tracked_idxs)]

        # output param ids
        self._output = None  # initialized during op logging
        self._output_tracked_idxs = None  # initialized during op logging
        self._output_param_ids = list()

        # op logging storage
        self._pid_to_functions_dict = dict()

        # temporary sub-graph storage
        self._tmp_sub_param_dict = dict()
        self._tmp_sub_functions = list()

        # graph storage
        self._param_dict = dict()
        self._functions = dict()
        self._num_functions = dict()
        self._max_subgraph_widths = dict()
        self._max_subgraph_heights = dict()

        # multiprocessing
        self._timeout = ivy.queue_timeout()
        self._num_workers = num_workers

        # connected flag
        self._connected = False

        # grouped functions
        self._grouped_functions = dict()

    # Properties #
    # -----------#

    @property
    def _all_grouped_functions(self):
        all_grouped_functions = list()
        for gfs in self._grouped_functions.values():
            for i, fs in enumerate(gfs):
                if len(all_grouped_functions) == i:
                    all_grouped_functions.append(list())
                all_grouped_functions[i] += fs
        return all_grouped_functions

    @property
    def _all_param_dict(self):
        all_param_dict = dict()
        for pd in self._param_dict.values():
            all_param_dict = {**all_param_dict, **pd}
        return all_param_dict

    @property
    def _all_functions(self):
        all_functions = list()
        for fn in self._functions.values():
            all_functions += fn
        return all_functions

    @property
    def _max_graph_width(self):
        return max([len(fns) for fns in self._all_grouped_functions]) if self._all_grouped_functions else 0

    @property
    def _max_graph_height(self):
        return len(self._all_grouped_functions)

    # Multiprocessing #
    # ----------------#

    def _initialize_multiprocessing(self):

        # prevent redundant workers by limiting to graph width
        self._num_workers =\
            min(self._num_workers, self._max_subgraph_widths[_terminal_pids_to_key(self._output_param_ids)])

        if self._num_workers <= 1:
            return

        # multiprocessing module
        multiprocessing = ivy.multiprocessing('fork')

        # initialize multi dict
        self._param_dict_multi = multiprocessing.Manager().dict(self._tmp_sub_param_dict)

        # create workers
        self._input_queues = list()
        self._output_queues = list()
        self._workers = list()
        for i in range(self._num_workers):
            input_queue = multiprocessing.Queue()
            output_queue = multiprocessing.Queue()
            worker = multiprocessing.Process(
                target=self._worker_fn, args=(
                    input_queue, output_queue, ivy.default_device(), self._tmp_sub_functions[i::self._num_workers],
                    ivy.current_framework_str()))
            worker.start()
            self._input_queues.append(input_queue)
            self._output_queues.append(output_queue)
            self._workers.append(worker)

    def _worker_fn(self, input_queue, output_queue, dev_str, functions, framework_str):
        ivy.set_framework(framework_str)
        ivy.set_default_device(dev_str)
        while True:
            try:
                input_queue.get(timeout=self._timeout)
            except queue.Empty:
                continue
            for fn in functions:
                arg_vals = [self.get_param_multi(pid) for pid in fn.arg_param_ids]
                kwarg_vals = [self.get_param_multi(pid) for pid in fn.kwarg_param_ids]
                ret = fn(arg_vals, kwarg_vals)
                if not isinstance(ret, tuple):
                    ret = (ret,)
                [self.set_param_multi(pid, ivy.index_nest(ret, idx))
                 for pid, idx in zip(fn.output_param_ids, fn.output_tracked_idxs)]
            output_queue.put(True)

    # Foward with Op Logging #
    # -----------------------#

    def _compute_return(self):
        ret = self._fn(*self._args, **self._kwargs)
        if not isinstance(ret, tuple):
            ret = (ret,)
        return ret

    def _register_output(self, ret):
        self._output = list(ret)
        self._output_tracked_idxs = ivy.nested_indices_where(
            ret, lambda x: ivy.is_array(x) or isinstance(x, self._stateful_classes))
        output_tracked_idxs = ivy.nested_indices_where(
            ret, lambda x: ivy.is_array(x) or isinstance(x, self._stateful_classes))
        self._output_param_ids = [_get_id(x) for x in ivy.multi_index_nest(list(ret), output_tracked_idxs)]

        # find any inputs which were fed directly to the output, and update pid and add identity function
        for i, pid in enumerate(self._output_param_ids):
            if pid in self._arg_param_ids + self._kwarg_param_ids:

                new_pid = random.randint(0, 2 ** 48)

                def new_fn(a, _):
                    return a[0]

                new_fn.arg_param_ids = [pid]
                new_fn.kwarg_param_ids = list()
                new_fn.output_param_ids = [new_pid]
                if pid in self._arg_param_ids:
                    index = self._arg_param_ids.index(pid)
                    output_param_type = self._arg_param_types[index]
                    output_param_shape = self._arg_param_shapes[index]
                else:
                    index = self._kwarg_param_ids.index(pid)
                    output_param_type = self._kwarg_param_types[index]
                    output_param_shape = self._kwarg_param_shapes[index]
                new_fn.output_param_types = [output_param_type]
                new_fn.fns_in = list()
                new_fn.output_tracked_idxs = [[0]]
                new_fn.output_param_shapes = [output_param_shape]

                self.add_fn_to_dict(new_pid, new_fn)
                self._output_param_ids[i] = new_pid

    # noinspection PyProtectedMember
    def log_all_ops(self):
        global op_logging
        op_logging = True
        self._register_output(self._compute_return())
        op_logging = False

    # Getters and Setters #
    # --------------------#

    # inference

    def get_param(self, pid):
        return self._tmp_sub_param_dict[pid].get()

    def set_param(self, pid, value):
        self._tmp_sub_param_dict[pid].set(value)

    # multiprocessing inference

    def get_param_multi(self, pid):
        # ToDo: make this more efficient
        while True:
            try:
                return self._param_dict_multi[pid].get()
            except IndexError:
                pass

    def set_param_multi(self, pid, value):
        # ToDo: make this more efficient
        param = self._param_dict_multi[pid]
        param.set(value)
        self._param_dict_multi[pid] = param

    # compiling

    def add_param(self, pid, ptype, tree_height, shape=None):
        self._tmp_sub_param_dict[pid] = Param(ptype, tree_height, shape)

    def increment_param_count(self, pid):
        self._tmp_sub_param_dict[pid].set_count(self._tmp_sub_param_dict[pid].count + 1)

    def add_fn_to_dict(self, pid, fn):
        self._pid_to_functions_dict[pid] = fn

    def get_param_recursive(self, pid, depth, receiving_fn=None):
        if pid in self._tmp_sub_param_dict:
            return
        if pid in self._pid_to_functions_dict:
            fn = self._pid_to_functions_dict[pid]
        else:
            if not ivy.exists(receiving_fn):
                idx = self._output_param_ids.index(pid)
                del self._output_tracked_idxs[idx]
                del self._output_param_ids[idx]
                return
            if pid in receiving_fn.arg_param_ids:
                idx = receiving_fn.arg_param_ids.index(pid)
                del receiving_fn.arg_tracked_idxs[idx]
                del receiving_fn.arg_param_ids[idx]
            if pid in receiving_fn.kwarg_param_ids:
                idx = receiving_fn.kwarg_param_ids.index(pid)
                del receiving_fn.kwarg_tracked_idxs[idx]
                del receiving_fn.kwarg_param_ids[idx]
            return
        fn.tree_depth = depth
        self._tmp_sub_functions.append(fn)
        [self.get_param_recursive(pid, depth + 1, fn) for pid in copy.copy(fn.arg_param_ids)]
        [self.get_param_recursive(pid, depth + 1, fn) for pid in copy.copy(fn.kwarg_param_ids)]
        [self.increment_param_count(pid) for pid in fn.arg_param_ids + fn.kwarg_param_ids]
        [self.add_param(pid, ptype, depth, shape)
         for pid, ptype, shape in zip(fn.output_param_ids, fn.output_param_types, fn.output_param_shapes)]
        return

    # debugging

    def params_all_empty(self):
        return min([len(param) == 0 for param in self._tmp_sub_param_dict.values()]) is True

    # Function creation #
    # ------------------#

    def _chain_functions(self, terminal_pids):

        # dict key
        dict_key = _terminal_pids_to_key(terminal_pids)

        # add input params to param dict
        [self.add_param(pid, ptype, 'leaf', shape) for pid, ptype, shape in
         zip(self._arg_param_ids, self._arg_param_types, self._arg_param_shapes)]
        [self.add_param(pid, ptype, 'leaf', shape) for pid, ptype, shape in
         zip(self._kwarg_param_ids, self._kwarg_param_types, self._kwarg_param_shapes)]

        # add stateful params to param dict
        [self.add_param(pid, ptype, 'leaf', shape) for pid, ptype, shape in
         zip(self._stateful_param_ids, self._stateful_classes, self._stateful_param_shapes)]

        # recursively chain the graph via backward traversal
        [self.get_param_recursive(pid, depth=0) for pid in terminal_pids]
        [self.increment_param_count(pid) for pid in terminal_pids]

        # assert there are some functions in the graph
        assert self._tmp_sub_functions, 'Tried to chain functions for an empty graph'

        # sort the param ids based on depth, in order of input to output
        max_depth = max([p.depth if isinstance(p.depth, int) else 1 for p in self._tmp_sub_param_dict.values()])
        for k, v in self._tmp_sub_param_dict.items():
            if v.depth == 'leaf':
                # noinspection PyProtectedMember
                self._tmp_sub_param_dict[k]._tree_depth = max_depth + 1

        self._tmp_sub_param_dict = {k: v for k, v in sorted(self._tmp_sub_param_dict.items(), key=lambda knv: -knv[1].depth)}

        # save this sub-graph in the param dict
        self._param_dict[dict_key] = self._tmp_sub_param_dict

        # function for storing function heights
        def store_fn_heights(fn):
            heights_in = [store_fn_heights(fn_in) for fn_in in fn.fns_in if fn_in in self._tmp_sub_functions]
            if heights_in:
                _height = max(heights_in) + 1
            else:
                _height = 0
            fn.tree_height = _height
            return _height

        # store function heights
        [store_fn_heights(self._pid_to_functions_dict[pid]) for pid in terminal_pids]

        # find the height of the tree
        max_tree_height = max([fn.tree_height for fn in self._tmp_sub_functions]) if self._tmp_sub_functions else -1

        # group the functions based on their height in the tree from the starting leaf nodes
        grouped_functions = list()
        for height in range(0, max_tree_height+1):
            fns = [fn for fn in self._tmp_sub_functions if fn.tree_height == height]
            if height == 0:
                fns = sorted(fns, key=lambda x: len(x.fns_in))
            else:
                fns_hm1 = grouped_functions[-1]
                # noinspection PyUnresolvedReferences
                leftmost_idxs =\
                    [max(enumerate([fn in fn_hm1.fns_out for fn_hm1 in fns_hm1 if hasattr(fn_hm1, 'fns_out')]),
                         key=lambda x: x[1])[0] for fn in fns]
                fns = [fn for fn, _ in sorted(zip(fns, leftmost_idxs), key=lambda x: x[1])]
            grouped_functions.append(fns)
        self._grouped_functions[dict_key] = grouped_functions

        # stack functions in the best order
        self._tmp_sub_functions = [i for sl in grouped_functions for i in sl]

        # update the total graph storage
        self._num_functions[dict_key] = len(self._tmp_sub_functions)
        self._functions[dict_key] = self._tmp_sub_functions

        # compute maximum width and height of the graph
        self._max_subgraph_widths[dict_key] =\
            max([len(fns) for fns in self._grouped_functions]) if self._grouped_functions else 0
        self._max_subgraph_heights[dict_key] = len(self._grouped_functions)

    def _call(self, *args, **kwargs):
        # ToDo: make this as efficient as possible; this is performed at runtime
        [self.set_param(pid, ivy.index_nest(args, idx))
         for pid, idx in zip(self._arg_param_ids, self._arg_tracked_idxs)]
        [self.set_param(pid, ivy.index_nest(kwargs, idx))
         for pid, idx in zip(self._kwarg_param_ids, self._kwarg_tracked_idxs)]
        # ToDo: change so continual resetting of fixed stateful objects as below is not required
        [self.set_param(pid, val)
         for pid, val in zip(self._stateful_param_ids, self._stateful)]
        for i, fn in enumerate(self._tmp_sub_functions):
            arg_vals = [self.get_param(pid) for pid in fn.arg_param_ids]
            kwarg_vals = [self.get_param(pid) for pid in fn.kwarg_param_ids]
            ret = fn(arg_vals, kwarg_vals)
            if not isinstance(ret, tuple):
                ret = (ret,)
            [self.set_param(pid, ivy.index_nest(ret, idx))
             for pid, idx in zip(fn.output_param_ids, fn.output_tracked_idxs)]
        ret_vals = [self.get_param(pid) for pid in self._output_param_ids]
        ivy.set_nest_at_indices(self._output, self._output_tracked_idxs, ret_vals)
        if len(self._output) == 1:
            return self._output[0]
        return self._output

    def _multi_call(self, *args, **kwargs):
        # ToDo: make this as efficient as possible; this is performed at runtime
        [self.set_param_multi(pid, ivy.index_nest(args, idx))
         for pid, idx in zip(self._arg_param_ids, self._arg_tracked_idxs)]
        [self.set_param_multi(pid, ivy.index_nest(kwargs, idx))
         for pid, idx in zip(self._kwarg_param_ids, self._kwarg_tracked_idxs)]
        [q.put(True) for q in self._input_queues]
        [q.get(timeout=None) for q in self._output_queues]
        ret_vals = [self.get_param_multi(pid) for pid in self._output_param_ids]
        ivy.set_nest_at_indices(self._output, self._output_tracked_idxs, ret_vals)
        if len(self._output) == 1:
            return self._output[0]
        return self._output

    def connect(self, output_connected_only=True):
        self._chain_functions(self._output_param_ids)
        if not output_connected_only:
            for pid, fn in self._pid_to_functions_dict.items():
                if fn.terminal:
                    self._chain_functions(fn.output_param_ids)
        self._initialize_multiprocessing()
        self._connected = True

    def compiled(self):
        if not self._connected:
            self.connect()
        if self._num_workers <= 1:
            return self._call
        return self._multi_call

    def _position_nodes(self, g, num_inputs, randomness_factor=0.75):

        pos_dict = dict()
        assert 0 <= randomness_factor <= 1

        # select position based on width and height of graph
        for height, fns in enumerate(self._all_grouped_functions):
            width = len(fns)
            for w, f in enumerate(fns):
                pos = np.array([(height+1) / self._max_graph_height, 0.5 if width == 1 else w / (width - 1)])
                h_delta = 0.5/self._max_graph_height
                h_rand = np.random.uniform(-h_delta, h_delta)
                w_delta = 0.5 if width == 1 else 0.5/(width-1)
                w_delta_low = 0 if w == 0 else -w_delta
                w_delta_high = 0 if w == 1 else w_delta
                w_rand = np.random.uniform(w_delta_low, w_delta_high)
                pos += np.array([h_rand, w_rand]) * randomness_factor
                pos_dict[(f.output_param_ids[0], f.__name__, _args_str_from_fn(f))] = pos

        # add inputs
        input_idx = 0
        for n in g.nodes:
            if n not in pos_dict and n[1] == 'input':
                pos = np.array([0., 0.5 if num_inputs == 1 else input_idx/(num_inputs-1)])
                h_delta = 0.5/self._max_graph_height
                h_rand = np.random.uniform(0, h_delta)
                w_delta = 0.5 if num_inputs == 1 else 0.5/(num_inputs-1)
                w_delta_low = 0 if input_idx == 0 else -w_delta
                w_delta_high = 0 if input_idx == 1 else w_delta
                w_rand = np.random.uniform(w_delta_low, w_delta_high)
                pos += np.array([h_rand, w_rand]) * randomness_factor
                pos_dict[n] = pos
                input_idx += 1

        # assert all positions are in range 0-1
        for pos in pos_dict.values():
            assert (0 <= pos.all() <= 1)

        return pos_dict

    def show(self, save_to_disk=False, with_edge_labels=True, with_arg_labels=True, output_connected_only=True):

        # ensure graph is connected
        if not self._connected:
            self.connect()

        # create directed networkX graph
        g = nx.DiGraph()

        def inp():
            pass

        inp.__name__ = 'input'

        for func in self._pid_to_functions_dict.values():
            if func not in self._tmp_sub_functions and output_connected_only:
                continue
            for pid_in in func.arg_param_ids + func.kwarg_param_ids:
                if pid_in in self._pid_to_functions_dict:
                    fn_in = self._pid_to_functions_dict[pid_in]
                    fn_pid = fn_in.output_param_ids[0]
                else:
                    fn_in = inp
                    fn_pid = pid_in
                start_args = _args_str_from_fn(fn_in)
                start_node = (fn_pid, ivy.default(fn_in.__name__, 'unnamed'), start_args)
                end_args = _args_str_from_fn(func)
                end_node = (func.output_param_ids[0], ivy.default(func.__name__, 'output'), end_args)
                g.add_edge(start_node, end_node)

        # num inputs
        if not self._grouped_functions:
            num_inputs = 0
        else:
            height_0_fns = [i for s in [gf[0] for gf in self._grouped_functions.values()] for i in s]
            input_param_ids = list()
            for fn in height_0_fns:
                input_param_ids += fn.arg_param_ids + fn.kwarg_param_ids
            input_param_ids = set(input_param_ids)
            num_inputs = len(input_param_ids)

        # show
        plt.cla()
        ax = plt.subplot(111)
        max_dim = max(self._max_graph_width, self._max_graph_height)
        ax.set_aspect(self._max_graph_width / self._max_graph_height)
        pos = self._position_nodes(g, num_inputs)
        nx.draw_networkx(g, arrows=True, pos=pos,
                         node_color=[(0., 200 / 255, 0.)]*len(g.nodes), node_shape='s',
                         edge_color=[(0., 100 / 255, 0.)]*len(g.edges),
                         labels={n: n[1].replace('_', '') for n in g.nodes}, node_size=[300/max_dim]*len(g.nodes),
                         font_size=12/max_dim, linewidths=1/max_dim, width=1/max_dim,
                         arrowsize=max(10/max_dim, 1))
        if with_edge_labels:
            edge_labels = dict()
            for edge in g.edges:
                node_in = edge[0]
                node_out = edge[1]
                if node_in[0] in self._pid_to_functions_dict:
                    producing_fn = self._pid_to_functions_dict[node_in[0]]
                    output_param_ids = producing_fn.output_param_ids
                else:
                    output_param_ids = self._arg_param_ids + self._kwarg_param_ids + self._stateful_param_ids
                consuming_fn = self._pid_to_functions_dict[node_out[0]]
                incoming_pids = consuming_fn.arg_param_ids + consuming_fn.kwarg_param_ids
                pids = [pid for pid in output_param_ids if pid in incoming_pids]
                params = [self._tmp_sub_param_dict[pid] for pid in pids]
                edge_labels[edge] = '_'.join([_param_to_label(p) for p in params])
            nx.draw_networkx_edge_labels(g, pos, edge_labels=edge_labels, font_size=10/max_dim)
        if with_arg_labels:
            font_size = 9/max_dim
            nx.draw_networkx_labels(
                g, pos={k: v - np.array([0., font_size/90]) for k, v in pos.items()}, font_size=font_size,
                font_color=(0., 100/255, 0.), labels={n: n[2] for n in g.nodes})
        pos_list = list(pos.values())
        pos_min = np.min(pos_list, axis=0)
        pos_max = np.max(pos_list, axis=0)
        ax.set_xlim(pos_min[0] - 0.2/max_dim, pos_max[0] + 0.2/max_dim)
        ax.set_ylim(pos_min[1] - 0.2/max_dim, pos_max[1] + 0.2/max_dim)
        plt.show()
        if save_to_disk:
            plt.savefig('graph_{}.png'.format(''.join([f.__name__.replace('_', '')[0] for f in self._tmp_sub_functions])),
                        bbox_inches='tight', dpi=1500)

    def __del__(self):
        if self._num_workers <= 1:
            return
        # noinspection PyBroadException
        try:
            for i, w in enumerate(self._workers):
                self._input_queues[i].put(None)
                w.join(timeout=0.25)
            for q in self._input_queues:
                q.cancel_join_thread()
                q.close()
            for q in self._output_queues:
                q.cancel_join_thread()
                q.close()
        except Exception:
            pass
        finally:
            for w in self._workers:
                if w.is_alive():
                    w.terminate()

    # Clearing #
    # ---------#

    def clear(self):
        self._tmp_sub_param_dict.clear()
        self._tmp_sub_functions.clear()


# Methods #

def _get_id(x):
    global wrapping_paused
    wrapping_paused = True
    if hasattr(x, 'param_id'):
        wrapping_paused = False
        return x.__dict__['param_id']
    wrapping_paused = False
    return id(x)


def _clone_param(x):
    global wrapping_paused
    wrapping_paused = True
    x_copy = ivy.copy_array(x) if ivy.is_array(x) else copy.copy(x)  # copy the param
    if hasattr(x, '__dict__'):
        x.__dict__['param_id'] = id(x_copy)  # update the id of the original param (for preserved stateful objects)
    wrapping_paused = False
    return x_copy


def _wrap_method_for_compiling(fn, graph, limit_attributes=True, stateful_classes=None):

    stateful_classes = tuple(ivy.default(stateful_classes, tuple()))

    if (inspect.isclass(fn) or (hasattr(fn, '__name__') and
                                ((fn.__name__[0] == '_' and fn.__name__ not in ARRAY_BUILTINS) or
                                 fn.__name__ in NON_WRAPPED_METHODS + ARRAYLESS_RET_METHODS)) or
            (hasattr(fn, 'wrapped_for_compiling') and fn.wrapped_for_compiling)):
        return fn

    # noinspection PyUnresolvedReferences,PyProtectedMember
    def _method_wrapped(*args, **kwargs):

        # if cloning a param currently, return directly via the original function
        global wrapping_paused
        if wrapping_paused:
            return fn(*args, **kwargs)

        # return if the wrapping is already happening on a higher level, and it's not a built-in which legitimately
        # might need to be nested, unless it's a built-in recursion loop (ie for __getattribute__) in which case return
        global wrapped_stack
        if wrapped_stack and (wrapped_stack[-1].__name__[0:2] != '__' or
                              (wrapped_stack[-1].__name__ == fn.__name__ and args == args and kwargs == kwargs)):
            return fn(*args, **kwargs)

        # attributes to ignore
        if fn.__name__ in ['__getattr__', '__setattr__', '__getattribute__']:
            att_name = args[1]
            # return if the attribute being retrieved is another built-in method
            if att_name[0:2] == '__':
                return fn(*args, **kwargs)
            # if the attribute is not recognized as one which can form part of the graph, then return
            if limit_attributes and att_name not in GRAPH_ATTRIBUTES[ivy.current_framework_str()]:
                return fn(*args, **kwargs)

        # otherwise, set wrapping as true
        wrapped_stack.append(fn)

        # immutable tuple to mutable list
        args = list(args)

        # get array idxs for positional args
        arg_tracked_idxs = ivy.nested_indices_where(
            args, lambda x: ivy.is_array(x) or isinstance(x, stateful_classes))
        arg_param_ids = [_get_id(x) for x in ivy.multi_index_nest(args, arg_tracked_idxs)]

        # get array idxs for key-word args
        kwarg_tracked_idxs = ivy.nested_indices_where(
            kwargs, lambda x: ivy.is_array(x) or isinstance(x, stateful_classes))
        kwarg_param_ids = [_get_id(x) for x in ivy.multi_index_nest(kwargs, kwarg_tracked_idxs)]

        # set the backend function
        backend_fn = fn

        # compute the return
        ret_raw = fn(*args, **kwargs)

        # provide return value for __setattr__
        if fn.__name__ == '__setattr__':
            ret_raw = args[0]

            # update the setattr method to return the object after attribute setting
            def backend_fn(__obj, __name, __value):
                setattr(__obj, __name, __value)
                return __obj

        # covert return to list
        ret_listified = False
        if isinstance(ret_raw, tuple):
            ret = list(ret_raw)
        else:
            ret = [ret_raw]
            ret_listified = True

        # get array idxs for return
        ret_tracked_idxs = ivy.nested_indices_where(ret, lambda x: ivy.is_array(x) or isinstance(x, stateful_classes))
        ret_param_ids = [_get_id(x) for x in ivy.multi_index_nest(ret, ret_tracked_idxs)]
        ret_param_types = [x.__class__ for x in ivy.multi_index_nest(ret, ret_tracked_idxs)]
        ret_param_shapes = [_get_shape(x) for x in ivy.multi_index_nest(ret, ret_tracked_idxs)]

        # clone the param when getting an attribute, to preserve uniqueness in the graph
        if fn.__name__ in ['__getattr__', '__getattribute__']:
            # update the param_id for each param in the retreived attribute in the graph
            ivy.map_nest_at_indices(ret, ret_tracked_idxs, _clone_param)

        # find all duplicate param ids from the input in the return
        duplicates = list()
        for i, ret_pid in enumerate(ret_param_ids):
            if ret_pid in arg_param_ids + kwarg_param_ids:
                duplicates.append(i)

        # clone all repeated return parameters to give unique parameter ids in the graph
        duplicate_tracked_idxs = [ret_tracked_idxs[i] for i in duplicates]
        ivy.map_nest_at_indices(ret, duplicate_tracked_idxs, _clone_param)

        # get return param ids
        ret_param_ids = [_get_id(x) for x in ivy.multi_index_nest(ret, ret_tracked_idxs)]

        # wrap the function
        def new_fn(arg_array_vals, kwarg_array_vals):
            # ToDo: make this as efficient as possible; this is performed at runtime
            ivy.set_nest_at_indices(args, arg_tracked_idxs, arg_array_vals)
            ivy.set_nest_at_indices(kwargs, kwarg_tracked_idxs, kwarg_array_vals)
            return backend_fn(*args, **kwargs)

        # add function attributes which inform about the arguments and returns

        new_fn.args = args
        new_fn.arg_tracked_idxs = arg_tracked_idxs
        new_fn.arg_param_ids = arg_param_ids

        new_fn.kwargs = kwargs
        new_fn.kwarg_tracked_idxs = kwarg_tracked_idxs
        new_fn.kwarg_param_ids = kwarg_param_ids

        new_fn.output_tracked_idxs = ret_tracked_idxs
        new_fn.output_param_ids = ret_param_ids
        new_fn.output_param_types = ret_param_types
        new_fn.output_param_shapes = ret_param_shapes

        new_fn.terminal = True

        fns_in = [graph._pid_to_functions_dict[pid]
                  for pid in arg_param_ids + kwarg_param_ids if pid in graph._pid_to_functions_dict]
        for fn_in in fns_in:
            fn_in.terminal = False
            if not hasattr(fn_in, 'fns_out'):
                fn_in.fns_out = list()
            if new_fn not in fn_in.fns_out:
                fn_in.fns_out.append(new_fn)

        new_fn.fns_in = fns_in

        new_fn.__repr__ = lambda: new_fn.__name__

        if hasattr(fn, '__name__'):
            new_fn.__name__ = fn.__name__

        # add to graph if compiling
        global op_logging
        if op_logging:

            # add this function to the graph for each output pid
            for pid in ret_param_ids:
                if pid in graph._pid_to_functions_dict:
                    graph._register_output(ret)
                    op_logging = False
                    _unwrap_methods_from_op_logging(list(graph._stateful_classes))
                    graph.show(save_to_disk=True)
                    raise Exception(
                        'tried to add {} to graph._functions_dict, but function {} with the same output pid {} '
                        'already exists!'.format(
                            new_fn.__name__ + '(*{}, **{})'.format(new_fn.args, new_fn.kwargs),
                            graph._pid_to_functions_dict[pid].__name__ + '(*{}, **{})'.format(
                                graph._pid_to_functions_dict[pid].args, graph._pid_to_functions_dict[pid].kwargs), pid))
                graph.add_fn_to_dict(pid, new_fn)

        # unset wrapping as true
        wrapped_stack.pop(-1)

        # return the function output
        return ret[0] if ret_listified else tuple(ret)

    if hasattr(fn, '__name__'):
        _method_wrapped.__name__ = fn.__name__
    _method_wrapped.wrapped_for_compiling = True
    _method_wrapped.inner_fn = fn
    return _method_wrapped


def _unwrap_method_from_compiling(method_wrapped):
    if not hasattr(method_wrapped, 'wrapped_for_compiling') or not method_wrapped.wrapped_for_compiling:
        return method_wrapped
    return method_wrapped.inner_fn


def _wrap_methods_for_op_logging(graph, stateful_classes=None):

    # wrap backend framework
    classes_to_wrap = [getattr(importlib.import_module(ctw[0]), ctw[1])
                       for ctw in CLASSES_TO_WRAP[ivy.current_framework_str()]]
    _wrap_or_unwrap_methods(
        lambda fn: _wrap_method_for_compiling(fn, graph), classes_to_wrap=classes_to_wrap, native=True)

    # wrap stateful classes
    stateful_classes = ivy.default(stateful_classes, [])
    for cls in stateful_classes:
        assert hasattr(cls, '__setattr__') and (hasattr(cls, '__getattr__') or hasattr(cls, '__getattribute__'))
        cls.__setattr__ = _wrap_method_for_compiling(
            cls.__setattr__, graph, limit_attributes=False, stateful_classes=stateful_classes)
        if hasattr(cls, '__getattr__'):
            cls.__getattr__ = _wrap_method_for_compiling(
                cls.__getattr__, graph, limit_attributes=False, stateful_classes=stateful_classes)
        if hasattr(cls, '__getattribute__'):
            cls.__getattribute__ = _wrap_method_for_compiling(
                cls.__getattribute__, graph, limit_attributes=False, stateful_classes=stateful_classes)


def _unwrap_methods_from_op_logging(stateful_classes=None):

    # unwrap backend framework
    classes_to_wrap = [getattr(importlib.import_module(ctw[0]), ctw[1])
                       for ctw in CLASSES_TO_WRAP[ivy.current_framework_str()]] + stateful_classes
    _wrap_or_unwrap_methods(
        lambda fn: _unwrap_method_from_compiling(fn), classes_to_wrap=classes_to_wrap, native=True)

    # unwrap stateful classes
    stateful_classes = ivy.default(stateful_classes, [])
    for cls in stateful_classes:
        assert hasattr(cls, '__setattr__') and (hasattr(cls, '__getattr__') or hasattr(cls, '__getattribute__'))
        cls.__setattr__ = _unwrap_method_from_compiling(cls.__setattr__)
        if hasattr(cls, '__getattr__'):
            cls.__getattr__ = _unwrap_method_from_compiling(cls.__getattr__)
        if hasattr(cls, '__getattribute__'):
            cls.__getattribute__ = _unwrap_method_from_compiling(cls.__getattribute__)


def _create_graph(fn, *args, stateful=None, num_workers=1, output_connected_only=True, **kwargs):

    # extra stateful instances modified in the graph
    stateful = ivy.default(stateful, [])

    # extract the associated stateful classes
    stateful_classes = [s.__class__ for s in stateful]

    # copy the states for resetting after forward pass and compilation
    state_copies = [copy.deepcopy(s.__dict__) for s in stateful]

    # construct the graph
    graph = Graph(fn, *args, **kwargs, stateful=stateful, num_workers=num_workers)

    # wrap all methods for operation logging
    _wrap_methods_for_op_logging(graph, stateful_classes)

    # forward pass through the graph, logging all operations
    graph.log_all_ops()

    # unwrap all methods, now all operations have been logged
    _unwrap_methods_from_op_logging(stateful_classes)

    # reset the stateful objects to their initial state, prior to compilation
    for s, sc in zip(stateful, state_copies):
        for k in list(s.__dict__.keys()):
            if k not in sc:
                del s.__dict__[k]
                continue
            s.__dict__[k] = sc[k]

    # connect graph
    graph.connect(output_connected_only)

    # reset all global compiler variables, just to be sure
    global wrapping_paused
    wrapping_paused = False
    global op_logging
    op_logging = False
    global wrapped_stack
    wrapped_stack.clear()

    # return graph
    return graph


def compile_graph(fn, *args, stateful=None, num_workers=1, **kwargs):

    # create graph
    graph = _create_graph(fn, *args, stateful=stateful, num_workers=num_workers, **kwargs)

    # compile the graph forward pass into an executable function
    return graph.compiled()


def show_graph(fn, *args, stateful=None, num_workers=1, save_to_disk=False, with_edge_labels=True, with_arg_labels=True,
               output_connected_only=True, **kwargs):

    # create graph
    graph = _create_graph(fn, *args, stateful=stateful, num_workers=num_workers,
                          output_connected_only=output_connected_only, **kwargs)

    # show the compiled graph
    graph.show(save_to_disk, with_edge_labels, with_arg_labels, output_connected_only)
