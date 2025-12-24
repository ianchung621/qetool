from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import numpy as np
import matplotlib.pyplot as plt


ConductivityComponent = Literal[
    "S_xx", "S_yy", "S_zz", "S_xy", "S_xz", "S_yz",
    "A_xy", "A_yz", "A_zx",
]

SigmaUnit = Literal["S/cm", "S/m", "s^-1"]


@dataclass(frozen=True)
class OpticsFiles:
    prefix: str
    base: Path

    def kubo_path(self, component: ConductivityComponent) -> Path:
        kind, ij = component.split("_", 1)
        return self.base / f"{self.prefix}-kubo_{kind}_{ij}.dat"

    def jdos_path(self) -> Path:
        return self.base / f"{self.prefix}-jdos.dat"


def _guess_prefix_from_cwd(cwd: Path) -> str:
    wins = list(cwd.glob("*.win"))
    if len(wins) != 1:
        raise RuntimeError("Cannot infer prefix uniquely; pass prefix explicitly.")
    return wins[0].stem


def _read_kubo_3col(path: Path, soc: bool) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    if not path.exists():
        raise FileNotFoundError(path)
    arr = np.loadtxt(path)
    if arr.ndim != 2 or arr.shape[1] < 3:
        raise ValueError(f"{path} must have ≥3 columns (E, Re, Im)")
    spin_channel = 1 if soc else 2
    return arr[:, 0], spin_channel*arr[:, 1], spin_channel*arr[:, 2]


def _sigma_unit_convert(
    sigma_s_per_cm: np.ndarray,
    out_unit: SigmaUnit,
) -> np.ndarray:
    """
    Convert Wannier90 optical conductivity to desired unit.

    Native unit (from postw90): S/cm
    """
    if out_unit == "S/cm":
        return sigma_s_per_cm

    if out_unit == "S/m":
        return sigma_s_per_cm * 100.0

    if out_unit == "s^-1":
        eps0 = 8.854_187_8128e-12  # F/m
        return sigma_s_per_cm * (100.0 / (4.0 * np.pi * eps0))

    raise ValueError(f"Unknown conductivity unit: {out_unit}")


def plot_conductivity(
    component: ConductivityComponent,
    prefix: str | None = None,
    jdos: bool = False,
    out_unit: SigmaUnit = "S/cm",
    save_png: str | None = None,
    display: bool = False,
    soc: bool = False,
) -> None:
    cwd = Path.cwd()
    prefix = prefix or _guess_prefix_from_cwd(cwd)
    files = OpticsFiles(prefix=prefix, base=cwd)

    energy_ev, sigma_re, sigma_im = _read_kubo_3col(files.kubo_path(component), soc)

    sigma_re = _sigma_unit_convert(sigma_re, out_unit)
    sigma_im = _sigma_unit_convert(sigma_im, out_unit)

    fig, ax = plt.subplots()

    tensor_index = component.split("_")[-1]
    ax.plot(energy_ev, sigma_re, color="blue", label=rf"Re $\sigma_{{{tensor_index}}}$")
    ax.plot(energy_ev, sigma_im, color="red", label=rf"Im $\sigma_{{{tensor_index}}}$")

    unit_label = {
        "S/cm": r"S/cm",
        "S/m": r"S/m",
        "s^-1": r"s$^{-1}$",
    }[out_unit]

    ax.set_xlabel("Energy (eV)", fontsize=14)
    ax.set_ylabel(rf"Optical conductivity ({unit_label})", fontsize=14)
    ax.set_title(prefix, fontsize=16)
    ax.legend(fontsize=12)
    ax.grid(True, alpha=0.2)

    if jdos:
        e_j, j = np.loadtxt(files.jdos_path(), unpack=True)
        ax2 = ax.twinx()
        ax2.plot(e_j, j, color="green", label="JDOS")
        ax2.set_ylabel("JDOS", fontsize=14)

        line = ax2.lines[-1]
        ax2.tick_params(axis="y", colors=line.get_color())
        ax2.yaxis.label.set_color(line.get_color())

    if display:
        plt.show()
    else:
        save_png = save_png or f"{prefix}_opt_cond_{component}.png"
        fig.savefig(save_png, bbox_inches="tight", dpi=200)
        plt.close(fig)
        print(f"Figure saved to {save_png}")