from dataclasses import dataclass
from pathlib import Path
import re
from typing import Iterable, Literal

import numpy as np
import matplotlib.pyplot as plt

_CM_TO_THZ = 0.0299792458
_CM_TO_EV = 1.239841984e-4
_CM_TO_MEV = _CM_TO_EV * 1e3
_RY_TO_EV = 13.605693122994
_EV_TO_CM = 8065.54429
_RY_TO_CM = _RY_TO_EV * _EV_TO_CM          # ≈ 109737.315685 cm^-1
_RY_TO_THZ = 3.289841960e3
_RY_TO_MEV = _RY_TO_EV * 1e3

def _convert_unit_from_cm(
    freq_cm: np.ndarray,
    unit: Literal["cm^-1", "eV", "meV", "Thz"],
) -> tuple[np.ndarray, str]:
    if unit == "cm^-1":
        return freq_cm, r"Frequency (cm$^{-1}$)"
    if unit == "Thz":
        return freq_cm * _CM_TO_THZ, "Frequency (THz)"
    if unit == "eV":
        return freq_cm * _CM_TO_EV, "Energy (eV)"
    if unit == "meV":
        return freq_cm * _CM_TO_MEV, "Energy (meV)"
    
    raise ValueError(f"Unsupported unit: {unit}")

@dataclass(frozen=True, slots=True)
class PhononPath:
    xticks: np.ndarray  # shape (n,)
    xlabels: list[str]  # len n


_HS_RE = re.compile(
    r"high-symmetry point:\s*"
    r"[-+0-9.eEdD]+\s+[-+0-9.eEdD]+\s+[-+0-9.eEdD]+\s+"
    r"x coordinate\s*([-+0-9.eEdD]+)"
)


def _guess_prefix(cwd: Path, ext: str) -> str:
    wins = list(cwd.glob(rf"*.{ext}"))
    if len(wins) != 1:
        raise RuntimeError(
            f"Cannot infer prefix uniquely from '*.{ext}' in {cwd}. "
            "Pass prefix explicitly."
        )
    return wins[0].stem


def _read_band(path: Path) -> tuple[np.ndarray, np.ndarray]:
    """
    Read columns: x, y1, y2, ..., yN
    """
    data = np.loadtxt(path)
    if data.ndim != 2 or data.shape[1] < 2:
        raise ValueError(f"Unexpected band file format: {path}")
    x_vals = data[:, 0].astype(float)
    ys = data[:, 1:].astype(float)
    return x_vals, ys

def _read_dos(path: Path) -> tuple[np.ndarray, np.ndarray]:
    """
    Read columns: E, dos, pdos
    """
    data = np.loadtxt(path)
    if data.ndim != 2 or data.shape[1] < 2:
        raise ValueError(f"Unexpected dos file format: {path}")
    E = data[:, 0].astype(float)
    dos = data[:, 1].astype(float)
    return E, dos

def _read_high_sym_xticks(path: Path) -> list[float]:
    """
    Parse matdyn.x high_symmetry output, e.g.
    high-symmetry point: ... x coordinate   4.5981
    """
    xs: list[float] = []
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            m = _HS_RE.search(line)
            if m:
                xs.append(float(m.group(1).replace("D", "E").replace("d", "e")))
    return xs


def _parse_matdyn_labels(matdyn_in: Path) -> list[str]:
    """
    Extract labels from the q-path block of matdyn.in.
    We look for lines like:
        0.000 0.000 0.000  50 !G
    Return the labels in order: ["G", "K", ...]
    """
    labels: list[str] = []
    if not matdyn_in.exists():
        return labels

    with matdyn_in.open("r", encoding="utf-8", errors="ignore") as f:
        lines = list(f)

    # find the first integer line after the "/" namelist end: that's the number of points
    end_idx = None
    for i, line in enumerate(lines):
        if line.strip().startswith("/"):
            end_idx = i
            break
    if end_idx is None:
        return labels

    npts = None
    for j in range(end_idx + 1, len(lines)):
        s = lines[j].strip()
        if not s or s.startswith(("!", "#")):
            continue
        try:
            npts = int(s.split()[0])
            start = j + 1
            break
        except ValueError:
            continue
    if npts is None:
        return labels

    for line in lines[start : start + npts]:
        if "!" in line:
            lab = line.split("!", 1)[1].strip()
            labels.append(_pretty_k_label(lab))
        else:
            labels.append("")
    return labels


def _pretty_k_label(label: str) -> str:
    """
    Normalize labels: G -> Γ, GAMMA -> Γ, keep others as-is.
    """
    s = label.strip()
    s_up = s.upper()
    if s_up in {"G", "GM", "GAMMA", r"\GAMMA", "Γ"}:
        return "Γ"
    return s


def _dedupe_consecutive(xs: Iterable[float], labels: list[str] | None = None) -> PhononPath:
    xs_list = list(xs)
    if not xs_list:
        return PhononPath(xticks=np.array([]), xlabels=[])

    keep_x: list[float] = [xs_list[0]]
    keep_i: list[int] = [0]
    for i in range(1, len(xs_list)):
        if abs(xs_list[i] - keep_x[-1]) > 1e-10:
            keep_x.append(xs_list[i])
            keep_i.append(i)

    if labels is None or not labels:
        keep_labels = ["" for _ in keep_x]
    else:
        # align length; matdyn labels count should match high_sym points
        # if mismatch, we still do a best-effort trunc/pad
        lab = labels[: len(xs_list)] + [""] * max(0, len(xs_list) - len(labels))
        keep_labels = [lab[i] for i in keep_i]

    return PhononPath(xticks=np.array(keep_x, dtype=float), xlabels=keep_labels)


def _infer_path(
    k_vals: np.ndarray,
    band_in: Path,
    high_sym: Path,
) -> PhononPath:
    """
    Priority:
      1) high_sym.txt (xticks) + matdyn.in labels
      2) matdyn.in labels only -> spread ticks uniformly from k_vals
      3) fallback: no ticks/labels
    """
    xs = _read_high_sym_xticks(high_sym) if high_sym.exists() else []
    labels = _parse_matdyn_labels(band_in) if band_in.exists() else []

    if xs:
        # typical: xs length == number of path points in matdyn.in
        return _dedupe_consecutive(xs, labels)

    if labels:
        # no high_sym: place ticks uniformly across x-range
        n = len(labels)
        x0, x1 = float(k_vals.min()), float(k_vals.max())
        xticks = np.linspace(x0, x1, n)
        return PhononPath(xticks=xticks, xlabels=labels)

    return PhononPath(xticks=np.array([]), xlabels=[])

_LAMBDA_RE = re.compile(
    r"Broadening\s+([0-9.]+)\s+lambda\s+([0-9.]+).*?omega_ln\s+\[K\]\s+([0-9.]+)",
    re.IGNORECASE,
)


def read_broadenings_from_lambda(path: Path = Path("lambda")) -> list[float]:
    """Parse broadenings from QE 'lambda' file."""
    txt = path.read_text()
    broads: list[float] = []
    for m in _LAMBDA_RE.finditer(txt):
        broads.append(float(m.group(1)))
    if not broads:
        raise ValueError("No broadenings found in lambda file.")
    return broads


def _read_a2f(path: Path) -> tuple[np.ndarray, np.ndarray]:
    """
    Read QE a2F.dos*.
    Returns:
      omega_Ry, a2F_total
    """
    rows: list[list[float]] = []

    with path.open("r") as f:
        for line in f:
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            if s.lower().startswith("lambda"):
                break
            parts = s.split()
            rows.append([float(x) for x in parts])

    data = np.asarray(rows, dtype=float)
    if data.ndim != 2 or data.shape[1] < 3:
        raise ValueError(f"Unexpected a2F format in {path}")

    omega = data[:, 0]
    a2f = data[:, 1]

    # numerical cleanup near zero
    a2f = np.clip(a2f, 0.0, None)
    return omega, a2f


def _convert_unit_from_ry(
    omega_ry: np.ndarray,
    unit: Literal["cm^-1", "eV", "Thz", "meV"],
) -> tuple[np.ndarray, str]:
    if unit == "cm^-1":
        return omega_ry * _RY_TO_CM, r"$\omega$ (cm$^{-1}$)"
    if unit == "Thz":
        return omega_ry * _RY_TO_THZ, r"$\omega$ (THz)"
    if unit == "meV":
        return omega_ry * _RY_TO_MEV, r"$\omega$ (meV)"
    if unit == "eV":
        return omega_ry * _RY_TO_EV, r"$\omega$ (eV)"
    raise ValueError(f"Unsupported unit: {unit}")

def plot_phonon_band(
    prefix: str | None = None,
    freq_gp: str | None = None,
    band_in: str = "matdyn.in",
    high_sym: str = "high_sym.txt",
    unit: Literal["cm^-1", "eV", "Thz","meV"] = "Thz",
    save_png: str | None = None,
    display: bool = False,
) -> None:
    cwd = Path.cwd()
    band_in_p = Path(band_in)
    high_sym_p = Path(high_sym)

    # --- resolve prefix / file paths ---
    prefix = prefix or _guess_prefix(cwd, "freq")
    freq_gp_p = Path(freq_gp) if freq_gp is not None else Path(f"{prefix}.freq.gp")
    if not freq_gp_p.exists():
        raise FileNotFoundError(f"Cannot find band file: {freq_gp_p}")

    # --- load raw data (cm^-1 from QE) ---
    k_vals, freq_cm = _read_band(freq_gp_p)

    # --- unit conversion ---
    freqs, ylabel = _convert_unit_from_cm(freq_cm, unit)

    # --- infer ticks/labels ---
    path = _infer_path(k_vals, band_in_p, high_sym_p)

    # --- plot ---
    fig, ax = plt.subplots()
    ax.plot(k_vals, freqs, color='b', lw=1.0)

    if path.xticks.size:
        ax.set_xticks(path.xticks)
        ax.set_xticklabels(path.xlabels)
        for x in path.xticks:
            ax.axvline(x, color="k", linestyle="--", lw=0.8)
        ax.set_xlim(float(path.xticks[0]), float(path.xticks[-1]))
    else:
        ax.set_xlim(float(k_vals.min()), float(k_vals.max()))

    ax.tick_params(axis="both", which="major", labelsize=12)
    ax.set_ylabel(ylabel, fontsize=14)
    ax.set_title(prefix, fontsize=16)

    if display:
        plt.show()
    else:
        out = save_png or f"{prefix}_phonon_band.png"
        fig.savefig(out, bbox_inches="tight")
        print(f"Figure saved to {out}")

def plot_phonon_dos(
    prefix: str | None = None,
    phonon_dos: str | None = None,
    energy_unit: Literal["cm^-1", "eV", "Thz","meV"] = "meV",
    save_png: str | None = None,
    display: bool = False,
):
    cwd = Path.cwd()
    prefix = prefix or _guess_prefix(cwd, "freq")
    phonon_dos_p = Path(phonon_dos) if phonon_dos is not None else Path(f"{prefix}.phonon.dos")
    E, dos = _read_dos(phonon_dos_p)
    E, xlabel = _convert_unit_from_cm(E, energy_unit)
    dos = dos/(_CM_TO_MEV)

    fig, ax = plt.subplots()
    ax.plot(E, dos, color='b', lw=1.0)
    ax.set_xlabel(xlabel, fontsize=14)
    ax.set_ylabel("DOS (states/meV/cell)", fontsize=14)
    ax.set_title(prefix, fontsize=16)

    if display:
        plt.show()
    else:
        out = save_png or f"{prefix}_phonon_dos.png"
        fig.savefig(out, bbox_inches="tight")
        print(f"Figure saved to {out}")

def plot_a2f(
    prefix: str | None = None,
    energy_unit: Literal["cm^-1", "eV", "Thz","meV"] = "meV",
    save_png: str | None = None,
    display: bool = False,
):
    lambda_path = Path("lambda")
    if not lambda_path.exists():
        raise FileNotFoundError("Missing 'lambda' file.")

    broadenings = read_broadenings_from_lambda(lambda_path)
    a2f_files = [Path(f"a2F.dos{i+1}") for i in range(len(broadenings))]
    for p in a2f_files:
        if not p.exists():
            raise FileNotFoundError(p)

    cwd = Path.cwd()
    prefix = prefix or _guess_prefix(cwd, "freq")

    fig, ax = plt.subplots()

    # colormap over broadenings
    cmap = plt.get_cmap("viridis")
    norm = plt.Normalize(min(broadenings), max(broadenings))

    for b, a2f_file in zip(broadenings, a2f_files):
        omega_ry, a2f = _read_a2f(a2f_file)
        E, xlabel = _convert_unit_from_ry(omega_ry, energy_unit)

        ax.plot(E, a2f, lw=1.2, color=cmap(norm(b)), label=f"{b:.3f}",)

    ax.set_xlabel(xlabel, fontsize=14)
    ax.set_ylabel(r"$\alpha^2F(\omega)$", fontsize=14)
    ax.set_title(prefix, fontsize=16)

    # compact legend (many curves)
    ax.legend(
        title="Broadening ($cm^{-1}$)",
        fontsize=9,
        title_fontsize=10,
        ncol=2,
        frameon=False,
    )

    if display:
        plt.show()
    else:
        out = save_png or f"{prefix}_a2f.png"
        fig.savefig(out, bbox_inches="tight")
        print(f"Figure saved to {out}")