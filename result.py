from __future__ import annotations
from typing import Generator, TypeVar, Generic, Callable, Iterable, List
from abc import ABC, abstractmethod

from utils import compose, curry


E = TypeVar("E")
F = TypeVar("F")
A = TypeVar("A")
B = TypeVar("B")


class ResultError(Exception):
    pass

class Result(ABC, Generic[A, E]):
    @abstractmethod
    def __init__(self):
        raise NotImplementedError

    @abstractmethod
    def map_ok(self, fn: Callable[[A], B]) -> Result[B, E]:
        raise NotImplementedError

    @abstractmethod
    def flat_map(self, fn: Callable[[A], Result[B, E]]) -> Result[B, E]:
        raise NotImplementedError

    @abstractmethod
    def map_error(self, fn: Callable[[E], F]) -> Result[A, F]:
        raise NotImplementedError

    @abstractmethod
    def flat_map_error(self, fn: Callable[[E], Result[A, F]]) -> Result[A, F]:
        raise NotImplementedError

    @abstractmethod
    def apply(self, functor: Result[Callable[[A], B], E]) -> Result[B, E]:
        raise NotImplementedError

    @abstractmethod
    def match(self, ok_fn: Callable[[A], B], error_fn: Callable[[E], B]) -> B:
        raise NotImplementedError

    @abstractmethod
    def is_ok(self) -> bool:
        raise NotImplementedError
    
    @abstractmethod
    def is_error(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def try_get(self) -> A:
        raise NotImplementedError

    def __or__(self, fn: Callable[[A], B | Result[B, E]]) -> Result[B, E]:
        return self.flat_map(fn)


class Ok(Result[A, E]):
    __value: A
    def __init__(self, value: A):
        self.__value = value
    
    @property
    def value(self):
        return self.__value

    def map_ok(self, fn: Callable[[A], B]) -> Result[B, E]:
        return Ok(fn(self.__value))

    def flat_map(self, fn: Callable[[A], Result[B, E]]) -> Result[B, E]:
        val = fn(self.__value)
        if not isinstance(val, Result):
            # raise TypeError("Return value of 'fn' function argument is not instance of Result")
            return Ok(val)
        return val

    def map_error(self, fn: Callable[[E], F]) -> Result[A, F]:
        return self

    def flat_map_error(self, fn: Callable[[E], Result[A, F]]) -> Result[A, F]:
        return self

    def apply(self, functor: Result[Callable[[A], B], E]) -> Result[B, E]:
        if isinstance(functor, Ok):
            return self.map_ok(functor.value)
        elif isinstance(functor, Error):
            return functor
        else:
            raise TypeError

    def match(self, ok_fn: Callable[[A], B], error_fn: Callable[[E], B]) -> B:
        return ok_fn(self.__value)

    @property
    def is_ok(self) -> bool:
        return True
    
    @property
    def is_error(self) -> bool:
        return False

    def try_get(self) -> A:
        return self.__value

    def __repr__(self):
        return f"Ok({self.__value!r})"

class Error(Result[A, E]):
    __error: E

    def __init__(self, error: E):
        self.__error = error

    @property
    def error(self):
        return self.__error

    def map_ok(self, fn: Callable[[A], B]) -> Result[B, E]:
        return self

    def flat_map(self, fn: Callable[[A], Result[B, E]]) -> Result[B, E]:
        return self

    def map_error(self, fn: Callable[[E], F]) -> Result[A, F]:
        return Error(fn(self.__error))

    def flat_map_error(self, fn: Callable[[E], Result[A, F]]) -> Result[A, F]:
        return fn(self.__error)

    def apply(self, functor: Result[Callable[[A], B], E]) -> Result[B, E]:
        if isinstance(functor, Ok):
            return self
        elif isinstance(functor, Error):
            return Error(functor.error + self.error)
        else:
            raise TypeError

    def match(self, ok_fn: Callable[[A], B], error_fn: Callable[[E], B]) -> B:
        return error_fn(self.__error)

    @property
    def is_ok(self) -> bool:
        return False
    
    @property
    def is_error(self) -> bool:
        return True

    def try_get(self) -> A:
        raise ResultError(self.__error)

    def __repr__(self):
        return f"Error({self.__error!r})"


def safe_wrap(fn: Callable[..., A]=None, errors_list=False) -> Callable[..., Result[A, Exception]]:
    def inner(*args, **kwargs):
        try:
            val = fn(*args, **kwargs)
            if isinstance(val, Result):
                return val
            else:
                return Ok(val)
        except Exception as e:
            if errors_list:
                return Error(e if not isinstance(e, Iterable) else [e])
            else:
                return Error(e)
    return inner

def match(ok_fn: Callable[[A], B], error_fn: Callable[[E], B]):
    def inner_match(result: Result[A, E]) -> B:
        return result.match(ok_fn, error_fn)
    return inner_match

def _map_ok(fn: Callable[[A], B], x: Result[A, E]) -> Result[B, E]:
    return x.map_ok(fn)
map_ok = curry(_map_ok)

def _flat_map(fn: Callable[[A], Result[B, E]], x: Result[A, E]) -> Result[B, E]:
    return x.flat_map(fn)
flat_map = curry(_flat_map)

def _map_error(fn: Callable[[E], F], x: Result[A, E]) -> Result[A, F]:
    return x.map_error(fn)
map_error = curry(_map_error)

def _apply(f: Result[Callable[[A], B], E], x: Result[A, E]) -> Result[B, E]:
    return x.apply(f)
apply = curry(_apply)

def __acc_fn(x): return __acc_fn
acc = Ok(__acc_fn)


def __appender(lst):
    """ WARNING - this function mutates a given list `lst`. It should not be used outside of traverse* function implementations"""
    def inner(value):
        lst.append(value)
        return lst
    return inner

def _traverse_monadic(fn: Callable[[A], Result[B, E]], seq: Iterable[Result[A, E]]) -> Result[List[B], E]:
    val = Ok([])
    for elem in seq:
        val = val.flat_map(lambda acc: elem.flat_map(fn).map_ok(__appender(acc)))
    return val
traverse_monadic = curry(_traverse_monadic)

def _traverse_applicative(fn: Callable[[A], Result[B, E]], seq: Iterable[Result[A, E]]) -> Result[List[B], E]:
    appender_ok = Ok(__appender)

    if not isinstance(seq, Iterable):
        raise TypeError(f"seq should be subclass of an Iterable. Given: {type(seq)}")

    accumulator = Ok([])
    for elem in seq:
        if not isinstance(elem, Result):
            raise TypeError(f"seq should contain values of Result type. Found element: {elem}")
        new_value = elem.flat_map(fn)
        accumulator = apply(apply(appender_ok, accumulator), new_value)
    return accumulator
traverse_applicative = curry(_traverse_applicative)

def aggregate(fn: Callable[[A], Result[B,E]]=None, seq: Iterable[Result[A, E]]=None, fail_fast=False) -> Result[List[B], E]:
    """ Iterates over a list of results in `seq`, applies given function to every value inside `Ok` element 
    and aggregates produced `Result`s into either: 
        1. if all original and produced results are Ok - Ok of a list of values contained in the produced results
        2. else: 
            - if fail_fast is False - Error of a list of all errors extracted from original or produced results
            - if fail_fast is True  - First Error produced by the given function `fn` or encountered in original `seq`, 
                while processing elements from the begining of a given `seq`

    If the function is not given - it defaults to `Ok`, 
    which means it will forward original result to the aggregator without changing it.

    Using non-default function is functionally equivalent to first `flat_map`ing `seq` 
    and then `aggregate`ing using default function
    """
    traverser = traverse_applicative if not fail_fast else traverse_monadic
    if not fn and not seq:
        return traverser(Ok)
    elif callable(fn) and not seq:
        return traverser(fn)
    elif isinstance(fn, Iterable) and not seq:
        seq = fn
        fn = Ok

    return traverser(fn, seq)


def from_generator(fn):
    def result_runner(*args, **kwargs):
        generator = fn(*args, **kwargs)
        if not isinstance(generator, Generator):
            if isinstance(generator, Result):
                return generator
            else:
                return Ok(generator)

        try:
            selector = next(generator)
            while True:
                if isinstance(selector, Ok):
                    selector = generator.send(selector.value)
                elif isinstance(selector, Error):
                    return selector
                else:
                    raise RuntimeError(
                        "Expected value yielded from generator to be Result. "
                        f"Instead got: {selector!r}"
                    )
        except StopIteration as e:
            if isinstance(e.value, Result):
                return e.value
            else:
                return Ok(e.value)
    return result_runner
