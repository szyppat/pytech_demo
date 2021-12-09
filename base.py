from __future__ import annotations
from dataclasses import dataclass
import traceback
from typing import TypeVar, Any, Type, List

import result


E = TypeVar('E', bound='DomainError')


@dataclass(frozen=True, eq=False)
class DomainError:
    stack: str
    msg: str

    @classmethod
    def create(cls: Type[E], msg) -> result.Error[Any, E]:
        return result.Error(cls(
            ''.join(traceback.format_stack()[:-1]),
            msg,
        ))

    def __repr__(self):
        return f"{self.__class__.__name__}(msg={self.msg})"

    def __str__(self):
        return self.msg

    def __eq__(self, other):
        return type(self) == type(other) and self.msg == other.msg

    def __add__(self, other: DomainError | list):
        if not isinstance(other, (DomainError, list)):
            raise TypeError(f"Cannot add DomainError to {type(other)}. Expected DomainError or List[DomainError]")

        if isinstance(other, DomainError):
            return [self, other]
        else:
            return [self, *other]

    def __radd__(self, other: DomainError | list):
        if not isinstance(other, (DomainError, list)):
            raise TypeError(f"Cannot add DomainError to {type(other)}. Expected DomainError or List[DomainError]")

        if isinstance(other, DomainError):
            return [other, self]
        else:
            return [*other, self]

    @classmethod
    def join_errors(cls: Type[E], msg: str):
        def joiner(errors: List[DomainError]) -> result.Error[Any, E]:
            errors = [errors] if isinstance(errors, DomainError) else errors
            return cls.create(msg + ":\n  " + ("\n  ".join(e.msg for e in errors)))
        return joiner
