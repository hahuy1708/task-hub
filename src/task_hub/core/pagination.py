from dataclasses import dataclass


@dataclass(frozen=True)
class Pagination:
    skip: int
    limit: int
