from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import numpy as np
import matplotlib.pyplot as plt


ConductivityComponentS = Literal["S_xx", "S_yy", "S_zz", "S_xy", "S_xz", "S_yz"]


@dataclass(frozen=True)
class OpticsFiles:
    prefix: str
    base: Path

    def kubo_path(self, component: ConductivityComponentS) -> Path:
        kind, ij = component.split("_", 1)
        return self.base / f"{self.prefix}-kubo_{kind}_{ij}.dat"


def _guess_prefix_from_cwd(cwd: Path) -> str:
    wins = list(cwd.glob("*.win"))
    if len(wins) != 1:
        raise RuntimeError("Cannot infer prefix uniquely; pass prefix explicitly.")
    return wins[0].stem


def _read_kubo_3col(path: Path, soc: bool) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    arr = np.loadtxt(path)
    if arr.ndim != 2 or arr.shape[1] < 3:
        raise ValueError(f"{path} must have ≥3 columns (E, Re, Im)")
    spin_channel = 1 if soc else 2
    return arr[:, 0], spin_channel*arr[:, 1], spin_channel*arr[:, 2]


def _sigma_s_per_cm_to_s_per_m(sigma_s_per_cm: np.ndarray) -> np.ndarray:
    return sigma_s_per_cm * 100.0


def _sigma_to_eps_si(
    energy_ev: np.ndarray,
    sigma_s_per_cm: np.ndarray,
    eps_inf: float = 1.0,
) -> np.ndarray:
    """
    ε(ω) = ε_inf + i σ(ω) / (ε0 ω), using SI units.
    energy_ev: ħω in eV
    sigma_s_per_cm: σ in S/cm (from Wannier90 manual)
    returns complex ε(ω)
    """
    eps0 = 8.854_187_8128e-12  # F/m
    hbar = 1.054_571_817e-34   # J*s
    e = 1.602_176_634e-19      # C

    omega = (energy_ev * e) / hbar  # rad/s
    sigma_si = _sigma_s_per_cm_to_s_per_m(sigma_s_per_cm)  # S/m

    eps = np.empty(energy_ev.shape, dtype=np.complex128)
    # avoid divide-by-zero at E=0
    mask = omega > 0.0
    eps[~mask] = np.nan
    eps[mask] = eps_inf + 1j * sigma_si[mask] / (eps0 * omega[mask])
    return eps


def plot_dielectric(
    component: ConductivityComponentS = "S_xx",
    prefix: str | None = None,
    eps_inf: float = 1.0,
    save_png: str | None = None,
    display: bool = False,
    soc: bool = False,
) -> None:
    cwd = Path.cwd()
    prefix = prefix or _guess_prefix_from_cwd(cwd)
    files = OpticsFiles(prefix=prefix, base=cwd)

    energy_ev, sig_re, sig_im = _read_kubo_3col(files.kubo_path(component), soc)
    sigma = sig_re + 1j * sig_im  # S/cm

    eps = _sigma_to_eps_si(energy_ev=energy_ev, sigma_s_per_cm=sigma, eps_inf=eps_inf)

    label_idx = component.split("_")[-1]

    fig, ax = plt.subplots()
    ax.plot(energy_ev, eps.real, color="blue", label=rf"Re $\varepsilon_{{{label_idx}}}$")
    ax.plot(energy_ev, eps.imag, color="red", label=rf"Im $\varepsilon_{{{label_idx}}}$")

    ax.set_xlabel("Energy (eV)", fontsize=14)
    ax.set_ylabel(r"Dielectric constant", fontsize=14)
    ax.set_title(prefix, fontsize=16)
    ax.legend(fontsize=12)
    ax.grid(True, alpha=0.2)

    if display:
        plt.show()
    else:
        save_png = save_png or f"{prefix}_dielectric_{component}.png"
        fig.savefig(save_png, bbox_inches="tight", dpi=200)
        plt.close(fig)
        print(f"Figure saved to {save_png}")