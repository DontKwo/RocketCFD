"""Post-processing sanity flags: negative drag, discontinuous sweep jumps, non-convergence."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

DEFAULT_DISCONTINUITY_THRESHOLD_PCT = 25.0
DEFAULT_CONVERGENCE_RESIDUAL = 1e-4


@dataclass
class SanityFlag:
    case_index: int
    message: str


@dataclass
class ForceMomentConvergence:
    converged: bool
    force_variation_pct: float
    moment_variation_pct: float
    sample_window: int
    reason: str


@dataclass
class ComprehensiveConvergenceAssessment:
    status: str
    residuals_converged: bool
    forces_converged: bool
    max_continuity_error: float | None
    details: list[str]


@dataclass
class SanityReport:
    flags: list[SanityFlag] = field(default_factory=list)

    @property
    def clean(self) -> bool:
        return len(self.flags) == 0


def check_negative_drag(cd_values: list[float]) -> list[SanityFlag]:
    return [
        SanityFlag(i, f"Cd is negative ({cd:.4g}); check reference-area sign convention and mesh orientation.")
        for i, cd in enumerate(cd_values)
        if cd < 0.0
    ]


def check_discontinuities(
    x_values: list[float], y_values: list[float], threshold_pct: float = DEFAULT_DISCONTINUITY_THRESHOLD_PCT
) -> list[SanityFlag]:
    """Flags adjacent sweep points sorted by x_values whose y_values jump by more than threshold_pct."""
    if len(x_values) < 2:
        return []
    order = np.argsort(x_values)
    y_sorted = np.asarray(y_values)[order]
    flags = []
    for i in range(1, len(y_sorted)):
        a, b = y_sorted[i - 1], y_sorted[i]
        scale = max(abs(a), abs(b), 1e-9)
        jump_pct = abs(b - a) / scale * 100.0
        if jump_pct > threshold_pct:
            flags.append(
                SanityFlag(
                    int(order[i]),
                    f"Discontinuous jump of {jump_pct:.0f}% between adjacent sweep points "
                    f"({a:.4g} -> {b:.4g}).",
                )
            )
    return flags


def check_convergence(
    residual_history: list[float], threshold: float = DEFAULT_CONVERGENCE_RESIDUAL
) -> SanityFlag | None:
    if not residual_history:
        return SanityFlag(-1, "No residual history found; cannot confirm convergence.")
    final = residual_history[-1]
    if final > threshold:
        return SanityFlag(-1, f"Final residual {final:.2e} is above the convergence threshold {threshold:.2e}.")
    return None


def check_force_moment_convergence(
    forces: np.ndarray,
    moments: np.ndarray,
    window_fraction: float = 0.2,
    max_variation_pct: float = 1.0,
) -> ForceMomentConvergence:
    """Evaluates whether forces and moments have stabilized asymptotically over recent iterations."""
    n_samples = len(forces)
    if n_samples < 5:
        return ForceMomentConvergence(
            converged=False,
            force_variation_pct=100.0,
            moment_variation_pct=100.0,
            sample_window=n_samples,
            reason="Insufficient time steps to evaluate asymptotic force stability.",
        )

    window = max(3, int(n_samples * window_fraction))
    f_tail = forces[-window:]
    m_tail = moments[-window:]

    f_mag = np.linalg.norm(f_tail, axis=-1) if f_tail.ndim > 1 else np.abs(f_tail)
    m_mag = np.linalg.norm(m_tail, axis=-1) if m_tail.ndim > 1 else np.abs(m_tail)

    f_scale = max(float(np.mean(f_mag)), 1e-6)
    m_scale = max(float(np.mean(m_mag)), 1e-6)

    f_var = float((np.max(f_mag) - np.min(f_mag)) / f_scale * 100.0)
    m_var = float((np.max(m_mag) - np.min(m_mag)) / m_scale * 100.0)

    converged = f_var <= max_variation_pct and m_var <= max_variation_pct
    reason = (
        f"Force variation {f_var:.2f}% and moment variation {m_var:.2f}% over last {window} steps."
        if converged
        else f"Asymptotic variation exceeds {max_variation_pct:.1f}% (force: {f_var:.1f}%, moment: {m_var:.1f}%)."
    )
    return ForceMomentConvergence(
        converged=converged,
        force_variation_pct=f_var,
        moment_variation_pct=m_var,
        sample_window=window,
        reason=reason,
    )


def assess_comprehensive_convergence(
    residual_history: dict[str, tuple[np.ndarray, np.ndarray]],
    forces_series: np.ndarray | None = None,
    moments_series: np.ndarray | None = None,
    residual_threshold: float = DEFAULT_CONVERGENCE_RESIDUAL,
) -> ComprehensiveConvergenceAssessment:
    """Assesses residual reduction, continuity errors, and asymptotic force stabilization."""
    details: list[str] = []
    res_converged = True
    max_cont: float | None = None

    if not residual_history:
        res_converged = False
        details.append("No residual history available.")
    else:
        for field_name, (_, values) in residual_history.items():
            if len(values) == 0:
                continue
            final_res = float(values[-1])
            if "continuity" in field_name.lower():
                max_cont = final_res
                if final_res > 1e-2:
                    res_converged = False
                    details.append(f"Cumulative continuity error {final_res:.2e} is elevated.")
            elif final_res > residual_threshold:
                res_converged = False
                details.append(f"Field '{field_name}' final residual {final_res:.2e} > {residual_threshold:.2e}.")

    forces_converged = True
    if forces_series is not None and moments_series is not None:
        f_eval = check_force_moment_convergence(forces_series, moments_series)
        forces_converged = f_eval.converged
        details.append(f_eval.reason)

    if res_converged and forces_converged:
        status = "CONVERGED"
    elif not res_converged and forces_converged:
        status = "FORCES_STABLE_RESIDUALS_HIGH"
    elif res_converged and not forces_converged:
        status = "OSCILLATORY_FORCES"
    else:
        status = "NON_CONVERGED"

    return ComprehensiveConvergenceAssessment(
        status=status,
        residuals_converged=res_converged,
        forces_converged=forces_converged,
        max_continuity_error=max_cont,
        details=details,
    )


def build_sanity_report(
    cd_values: list[float], x_values: list[float], discontinuity_threshold_pct: float = DEFAULT_DISCONTINUITY_THRESHOLD_PCT
) -> SanityReport:
    flags = check_negative_drag(cd_values) + check_discontinuities(x_values, cd_values, discontinuity_threshold_pct)
    return SanityReport(sorted(flags, key=lambda f: f.case_index))
