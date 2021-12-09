from __future__ import annotations
from dataclasses import dataclass
import inspect
import functools
from typing import Callable, Iterable, List, TypeVar, Generic, overload

A = TypeVar('A')
B = TypeVar('B')
C = TypeVar('C')
D = TypeVar('D')
E = TypeVar('E')
R = TypeVar('R', covariant=True)
X = TypeVar('X', contravariant=True)
Y = TypeVar('Y', contravariant=True)
Z = TypeVar('Z', contravariant=True)

@overload
def curry(fn: Callable[[X], R]) -> Callable[[X], R]: ...
@overload
def curry(fn: Callable[[X, Y], R]) -> Callable[[X], Callable[[Y], R]]: ...
@overload
def curry(fn: Callable[[X, Y, Z], R]) -> Callable[[X], Callable[[Y], Callable[[Z], R]]]: ...

def curry(wrapped_fn, arity=None):
    n_args = len(inspect.getfullargspec(wrapped_fn).args) if arity is None else arity
    @functools.wraps(wrapped_fn)
    def curried(first_arg, *args):
        if n_args == len(args) + 1:
            return wrapped_fn(first_arg, *args)

        return curry(functools.partial(wrapped_fn, first_arg, *args), n_args - (1 + len(args)))
    return curried

def pipe(x, *fs):
    for f in fs:
        x = f(x)
    return x


@overload
def compose(a: Callable[[A], B], b: Callable[[B], C]) -> Callable[[A], C]: ...
@overload
def compose(a: Callable[[A], B], b: Callable[[B], C], c: Callable[[C], D]) -> Callable[[A], D]: ...
@overload
def compose(a: Callable[[A], B], b: Callable[[B], C], c: Callable[[C], D], d: Callable[[D], E]) -> Callable[[A], E]: ...

def compose(*fs):
    f, *rest_fs = fs
    def composed(*args, **kwargs):
        x = f(*args, **kwargs)
        return pipe(x, *rest_fs)
    return composed


def compose_right(*fs):
    f, *rest_fs = list(reversed(fs))
    def composed(*args, **kwargs):
        x = f(*args, **kwargs)
        return pipe(x, *rest_fs)
    return composed


def cmap(function: Callable[[A], B]):
    """Curried version of builtin map function"""
    def inner_map(sequence: Iterable[A]) -> Iterable[B]:
        return map(function, sequence)
    return inner_map


def cfilter(function: Callable[[A], bool]):
    """Curried version of builtin filter function"""
    def inner_filter(sequence: Iterable[A]) -> Iterable[A]:
        return filter(function, sequence)
    return inner_filter
