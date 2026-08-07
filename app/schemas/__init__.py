from pydantic import BaseModel as _BaseModel


class StrictModel(_BaseModel):
    """Base model that disables Pydantic's protected namespace checks.

    Many schemas use fields like ``model_id``, ``model_name``, etc. which
    conflict with Pydantic v2's default ``model_`` protected namespace.
    Using this base class silences those warnings.
    """

    model_config = {"protected_namespaces": ()}
