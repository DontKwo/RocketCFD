"""Results-table formatting and CSV export for OpenFoamCaseResult sweeps."""
from __future__ import annotations

from collections.abc import Callable

from rocketcfd.aerotable import write_aerotable_csv
from rocketcfd.openfoam.case_result import OpenFoamCaseResult

RESULT_QUANTITIES: dict[str, Callable[[OpenFoamCaseResult], float]] = {
    "Cd": lambda case: case.coefficients.cd,
    "Cl": lambda case: case.coefficients.cl,
    "Cs": lambda case: case.coefficients.cs,
    "Cmx": lambda case: float(case.coefficients.cm[0]),
    "Cmy": lambda case: float(case.coefficients.cm[1]),
    "Cmz": lambda case: float(case.coefficients.cm[2]),
    "Fx (N)": lambda case: float(case.force[0]),
    "Fy (N)": lambda case: float(case.force[1]),
    "Fz (N)": lambda case: float(case.force[2]),
    "Mx (N*m)": lambda case: float(case.moment[0]),
    "My (N*m)": lambda case: float(case.moment[1]),
    "Mz (N*m)": lambda case: float(case.moment[2]),
    "Mach": lambda case: case.condition.mach(),
    "Dynamic pressure (Pa)": lambda case: case.condition.dynamic_pressure(),
    "Reference area (m^2)": lambda case: case.reference_area,
    "Reference length (m)": lambda case: case.reference_length,
}

RESULT_HEADERS = ["Case", "Solver"] + list(RESULT_QUANTITIES.keys())

CONDITION_QUANTITIES: dict[str, Callable[[OpenFoamCaseResult], float]] = {
    "Velocity (m/s)": lambda case: case.condition.velocity,
    "Alpha (deg)": lambda case: case.condition.alpha_deg,
    "Beta (deg)": lambda case: case.condition.beta_deg,
    "Density (kg/m^3)": lambda case: case.condition.density,
    "Temperature (K)": lambda case: case.condition.temperature,
}

PLOT_X_QUANTITIES: dict[str, Callable[[OpenFoamCaseResult], float]] = {**CONDITION_QUANTITIES, **RESULT_QUANTITIES}


def format_case_table_rows(case_results: list[OpenFoamCaseResult]) -> list[list[str]]:
    """Format sweep case results as string rows aligned with RESULT_HEADERS."""
    rows: list[list[str]] = []
    for case in case_results:
        values = [f"{extractor(case):.4g}" for extractor in RESULT_QUANTITIES.values()]
        rows.append([case.condition.name, case.application, *values])
    return rows


def export_case_results_csv(path: str, case_results: list[OpenFoamCaseResult]) -> None:
    """Export aerodynamic force and moment sweep results to CSV."""
    write_aerotable_csv(path, case_results, solver_regimes=[case.application for case in case_results])
