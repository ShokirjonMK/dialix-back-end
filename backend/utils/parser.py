import logging
import typing as t
from sqlalchemy import asc, desc


def parse_order_by(model, order_by: t.Optional[list[str]]):
    if not order_by:
        return []

    order_clauses = []
    for field in order_by:
        parts = field.split("_")
        logging.info(f"{parts=}")

        if len(parts) < 2 or parts[-1] not in {"asc", "desc"}:
            raise ValueError(f"Invalid order_by format: {field}")

        direction = parts[-1]
        parts.pop(-1)
        column_name = "_".join(parts)
        logging.info(f"{column_name=} {direction=}")

        column = getattr(model, column_name, None)
        if column is None:
            raise ValueError(f"Invalid order_by field: {column_name}")

        order_clauses.append(asc(column) if direction == "asc" else desc(column))

    return order_clauses
