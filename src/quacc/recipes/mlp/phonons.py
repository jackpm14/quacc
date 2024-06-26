"""Phonon recipes for MLPs."""

from __future__ import annotations

from importlib.util import find_spec
from typing import TYPE_CHECKING

from monty.dev import requires

from quacc import flow
from quacc.recipes.common.phonons import phonon_subflow
from quacc.recipes.mlp.core import relax_job, static_job
from quacc.utils.dicts import recursive_dict_merge
from quacc.wflow_tools.customizers import customize_funcs

has_deps = find_spec("phonopy") is not None and find_spec("seekpath") is not None

if TYPE_CHECKING:
    from typing import Any, Callable, Literal

    from ase.atoms import Atoms

    from quacc.schemas._aliases.phonons import PhononSchema


@flow
@requires(
    has_deps,
    message="Phonopy and seekpath must be installed. Run `pip install quacc[phonons]`",
)
def phonon_flow(
    atoms: Atoms,
    method: Literal["mace-mp-0", "m3gnet", "chgnet"],
    symprec: float = 1e-4,
    min_lengths: float | tuple[float, float, float] | None = 20.0,
    supercell_matrix: (
        tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]] | None
    ) = None,
    displacement: float = 0.01,
    t_step: float = 10,
    t_min: float = 0,
    t_max: float = 1000,
    run_relax: bool = True,
    job_params: dict[str, dict[str, Any]] | None = None,
    job_decorators: dict[str, Callable | None] | None = None,
) -> PhononSchema:
    """
    Carry out a phonon workflow, consisting of:

    1. Optional relaxation.
        - name: "relax_job"
        - job: [quacc.recipes.mlp.core.relax_job][]

    2. Generation of supercells.

    3. Static calculations on supercells
        - name: "static_job"
        - job: [quacc.recipes.mlp.core.static_job][]

    4. Calculation of thermodynamic properties.

    Parameters
    ----------
    atoms
        Atoms object
    method
        Universal ML interatomic potential method to use
    symprec
        Precision for symmetry detection.
    min_lengths
        Minimum length of each lattice dimension (A).
    supercell_matrix
        The supercell matrix to use. If specified, it will override any
        value specified by `min_lengths`.
    displacement
        Atomic displacement (A).
    t_step
        Temperature step (K).
    t_min
        Min temperature (K).
    t_max
        Max temperature (K).
    job_params
        Custom parameters to pass to each Job in the Flow. This is a dictinoary where
        the keys are the names of the jobs and the values are dictionaries of parameters.
    job_decorators
        Custom decorators to apply to each Job in the Flow. This is a dictionary where
        the keys are the names of the jobs and the values are decorators.

    Returns
    -------
    PhononSchema
        Dictionary of results from [quacc.schemas.phonons.summarize_phonopy][].
        See the type-hint for the data structure.
    """
    calc_defaults = {
        "relax_job": {"method": method, "opt_params": {"fmax": 1e-3}},
        "static_job": {"method": method},
    }
    job_params = recursive_dict_merge(calc_defaults, job_params)

    relax_job_, static_job_ = customize_funcs(
        ["relax_job", "static_job"],
        [relax_job, static_job],
        parameters=job_params,
        decorators=job_decorators,
    )

    return phonon_subflow(
        atoms,
        static_job_,
        relax_job=relax_job_ if run_relax else None,
        symprec=symprec,
        min_lengths=min_lengths,
        supercell_matrix=supercell_matrix,
        displacement=displacement,
        t_step=t_step,
        t_min=t_min,
        t_max=t_max,
        additional_fields={"name": f"{method} Phonons"},
    )
