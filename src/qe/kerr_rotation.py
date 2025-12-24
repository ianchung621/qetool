from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import numpy as np
import matplotlib.pyplot as plt


@dataclass(frozen=True)
class KerrData:
    energy: np.ndarray
    rotation: np.ndarray        # Re(kerr)
    ellipticity: np.ndarray     # Im(kerr)
    eps_xx: np.ndarray          # complex dielectric eps_xx
    n_xx: np.ndarray            # complex refractive index n_xx


def _read_energy_re_im(path: Path) -> tuple[np.ndarray, np.ndarray]:
    """
    Read 3 columns: energy, real, imag -> complex array.
    """
    data = np.loadtxt(path)
    if data.ndim != 2 or data.shape[1] < 3:
        raise ValueError(f"Expected 3 columns (E, Re, Im) in {path}, got shape={data.shape}")

    energy = data[:, 0].astype(float)
    val = data[:, 1].astype(float) + 1j * data[:, 2].astype(float)
    return energy, val


def _compute_kerr(
    energy: np.ndarray,
    s_xx: np.ndarray,
    s_xy: np.ndarray,
    *,
    prefactor: float = 0.00743403,
) -> KerrData:
    """
    Fortran algebra:
      eps_xx = 1 + i * s_xx * prefactor / E
      n_xx   = sqrt(eps_xx)
      kerr   = - s_xy / (s_xx * n_xx)
    """
    eps_xx = 1.0 + 1j * s_xx * (prefactor / energy)
    n_xx = np.sqrt(eps_xx)

    denom = s_xx * n_xx
    kerr = -s_xy / denom

    return KerrData(
        energy=energy,
        rotation=kerr.real,
        ellipticity=kerr.imag,
        eps_xx=eps_xx,
        n_xx=n_xx,
    )

def _guess_prefix_from_cwd(cwd: Path) -> str:
    wins = list(cwd.glob("*.win"))
    if len(wins) != 1:
        raise RuntimeError("Cannot infer prefix uniquely; pass prefix explicitly.")
    return wins[0].stem

def plot_kerr_rotation(
    prefix: str | None = None,
    unit: Literal["deg", "rad"] = "deg",
    save_png: str | None = None,
    display: bool = False,
) -> None:
    """
    Read Kubo outputs and plot Kerr rotation/ellipticity.

    Expected files (3 columns: energy, real, imag):
      - {prefix}-kubo_S_xx.dat
      - {prefix}-kubo_A_xy.dat
    """
    cwd = Path.cwd()
    prefix = prefix or _guess_prefix_from_cwd(cwd)

    base = Path(prefix)
    sxx_path = base.with_name(f"{base.name}-kubo_S_xx.dat")

    # Your prompt only specified S_xx filename. Common pair is A_xy.
    # If your file is named differently, edit this line.
    sxy_path = base.with_name(f"{base.name}-kubo_A_xy.dat")

    energy_xx, s_xx = _read_energy_re_im(sxx_path)
    energy_xy, s_xy = _read_energy_re_im(sxy_path)

    if energy_xx.shape != energy_xy.shape or not np.allclose(energy_xx, energy_xy, atol=1e-10, rtol=0.0):
        raise ValueError("Energy grids in S_xx and A_xy files do not match.")

    out = _compute_kerr(energy_xx, s_xx, s_xy)

    scale = 1.0 if unit == "rad" else (180.0 / np.pi)
    rotation = out.rotation * scale
    ellipticity = out.ellipticity * scale

    fig, ax = plt.subplots(figsize=(6.5, 4.0))
    ax.plot(out.energy, rotation, color="blue", label="Kerr rotation $θ_K$")
    ax.plot(out.energy, ellipticity, color="red", label="Kerr ellipticity $ε_K$")
    ax.set_xlabel("Energy (eV)", fontsize=14)
    ax.set_ylabel(f"Angle ({unit})", fontsize=14)
    ax.set_title(prefix, fontsize=16)
    ax.grid(True, alpha=0.2)
    ax.legend(fontsize=12)

    if display:
        plt.show()
        return

    save_png = save_png or f"{base.name}_kerr.png"
    fig.savefig(save_png, bbox_inches="tight", dpi=200)
    plt.close(fig)
    print(f"Figure saved to {save_png}")