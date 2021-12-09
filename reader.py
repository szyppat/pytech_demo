from __future__ import annotations
from typing import Callable, Generator, Generic, TypeVar, Union
from dataclasses import dataclass

A = TypeVar('A')
B = TypeVar('B')
C = TypeVar('C')

I = TypeVar('I')
O = TypeVar('O')
Fun = Callable[[I], O]


@dataclass(frozen=True)
class Reader(Generic[A, B]):
    fun: Fun[A, B]

    @staticmethod
    def create(value: B) -> Reader[A, B]:
        def _inner(_env: A):
            return value

        return Reader(_inner)

    def map(self, f: Fun[B, C]) -> Reader[A, C]:
        return Reader(lambda env: f(self.run(env)))

    def flat_map(self, f: Fun[B, Reader[A, C]]) -> Reader[A, C]:
        def mapped(env: A):
            g = f(self.run(env))
            return g.run(env)
        return Reader(mapped)

    def run(self, env: A) -> B:
        generator = self.fun(env)
        if not isinstance(generator, Generator):
            return generator

        selector = next(generator)
        try:
            while True:
                selector = selector if isinstance(selector, Reader) else Reader(selector)
                selector = generator.send(selector.run(env))
        except StopIteration as e:
            if isinstance(e.value, Reader):
                return e.value.run(env)
            else:
                return e.value

    def compose(self, other: Reader[A, Fun[I, O]]) -> Reader[A, C]:
        if not isinstance(other, Reader) and isinstance(other, Callable):
            other = Reader.create(other)
        def inner(env):
            f = self.run(env)
            g = other.run(env)
            return lambda arg: Reader.create(f(arg)).map(g).run(env)
        return Reader(inner)

    __rshift__ = compose

    def then(self, other: Fun[B, C] | Reader[A, Fun[B, C]]) -> Reader[A, C]:
        def inner(env):
            g = other.run(env) if isinstance(other, Reader) else other
            v = self.run(env)
            return g(v)
        return Reader(inner)

    __or__ = then

    def apply(self, other: I | Reader[A, I]) -> Reader[A, O]:
        def inner(env: A):
            f: Fun[I, O] = self.run(env)
            v = other.run(env) if isinstance(other, Reader) else other
            return f(v)
        return Reader(inner)

    __xor__ = apply

    def __call__(self, *args):
        r = self
        for arg in args:
           r = r.apply(arg)
        return r
