import re
import csv
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

# =====================================================================
# 1. PREP STAGE  —  generate scaled inputs from scf.in
# =====================================================================

CELL_PATTERN = re.compile(
    r"^\s*CELL_PARAMETERS\s*(?:\(?\s*angstrom\s*\)?)?\s*$", re.IGNORECASE
)

def prepare_scaled_inputs(scf_in: Path, scales: list[float]) -> list[Path]:
    """
    Read scf.in (must contain 'CELL_PARAMETERS (angstrom)'),
    scale its 3 lattice vectors by each factor in `scales`,
    and write a<scale>_scf.in (e.g. a0.97_scf.in).
    """
    lines = scf_in.read_text().splitlines(keepends=True)
    # locate CELL_PARAMETERS line
    for i, line in enumerate(lines):
        if CELL_PATTERN.match(line):
            start = i + 1
            break
    else:
        raise ValueError("CELL_PARAMETERS (angstrom) not found in scf.in")

    # extract 3x3 matrix
    cell_lines = lines[start:start + 3]
    cell = np.array([[float(x) for x in l.split()[:3]] for l in cell_lines])

    written = []
    for s in scales:
        scaled = cell * s
        new_lines = [f"  {v[0]:.8f}  {v[1]:.8f}  {v[2]:.8f}\n" for v in scaled]

        scaled_text = list(lines)
        scaled_text[start:start + 3] = new_lines
        out_path = scf_in.parent / f"a{str(s).rstrip('0').rstrip('.')}_scf.in"
        out_path.write_text("".join(scaled_text))
        written.append(out_path)
    
    print("# ====== QE bulk-modulus run script ======")
    print('PWX= # your pw.x executable path, e.g. $HOME/qe-7.4.1/bin/pw.x')
    print()
    for p in written:
        name = p.stem  # e.g. a0.97_scf
        print(f"mpirun -np 8 $PWX -in {p.name} > {name}.out")
    print("# =========================================")

    return written

# =====================================================================
# 2. ANALYSIS STAGE — parse energies and volumes, fit E(V), compute B
# =====================================================================

# ============================================================
#   1. Extract E(s) from QE outputs
# ============================================================

_A_PREFIX_RE = re.compile(r"a([0-9.]+)")

def extract_scale_from_name(name: str) -> float:
    """Extract lattice scale factor s from filename head 'a<value>_'."""
    m = _A_PREFIX_RE.search(Path(name).name)
    if not m:
        raise ValueError(f"Cannot parse scale from filename: {name}")
    return float(m.group(1))

_RE_ENE = re.compile(r"^\s*!\s+total energy\s*=\s*([-\d.]+)\s+Ry", re.IGNORECASE)

def read_energies_from_outs(pattern: str = "a*_scf.out") -> tuple[np.ndarray, np.ndarray, list[Path]]:
    """
    Parse energies from QE .out files.
    Volume is inferred from scale^3, not from printed 'unit-cell volume'.
    Returns arrays: (Vnorm, E), and list of paths.
    """
    outs = sorted(Path(".").glob(pattern))
    if not outs:
        raise FileNotFoundError(f"No output files matched pattern '{pattern}'")

    scales, energies, paths = [], [], []
    for p in outs:
        s = extract_scale_from_name(p.stem)
        E = None
        for line in p.open("r", errors="ignore"):
            m = _RE_ENE.match(line)
            if m:
                E = float(m.group(1))
                break
        if E is None:
            print(f"[skip] No energy found in {p.name}")
            continue
        scales.append(s)
        energies.append(E)
        paths.append(p)

    if len(scales) < 3:
        raise RuntimeError("Need at least 3 finished outputs for fitting.")
    Vnorm = np.array(scales) ** 3
    return Vnorm, np.array(energies), paths

# --- add/replace these regexes at top ---
_RE_ENE_BANG = re.compile(r"^\s*!\s+total energy\s*=\s*([-\d.]+)\s+Ry", re.IGNORECASE)
_RE_MAG_TOTAL = re.compile(r"^\s*total magnetization\s*=\s*([-\d.]+)\s+Bohr", re.IGNORECASE)


def _parse_energy_mag_from_out(path: Path) -> tuple[float | None, float | None]:
    """
    Parse QE .out and return (E_Ry, M_Bohr) from the *same* block that starts with '! total energy'.
    We take the first '! total energy' encountered, then scan until the next '!' (or EOF)
    and pick the first 'total magnetization' within that region.
    """
    lines = path.read_text(errors="ignore").splitlines()
    n = len(lines)
    i = 0
    while i < n:
        mE = _RE_ENE_BANG.match(lines[i])
        if not mE:
            i += 1
            continue

        # Found a '! total energy' → start of block
        E = float(mE.group(1))
        M = None

        j = i + 1
        while j < n:
            # Stop this block if we encounter the start of the next '!' energy line
            if _RE_ENE_BANG.match(lines[j]):
                break
            # Capture the first 'total magnetization' within this block
            mM = _RE_MAG_TOTAL.match(lines[j])
            if mM and M is None:
                M = float(mM.group(1))
                # don't break; still allow early exit on next '!' detection (but we already have M)
            j += 1

        return E, M  # only the first completed block is used

    return None, None  # no '! total energy' found


def read_energy_magnetization(pattern: str = "a*_scf.out"):
    """
    Collect (V/V0, E, M) from outputs.
    - Volume is normalized: V/V0 = s^3 from filename 'a<scale>_...'
    - Energy from the '! total energy' line
    - Magnetization from the same '! ...' block
    """
    outs = sorted(Path(".").glob(pattern))
    if not outs:
        raise FileNotFoundError(f"No output files matched pattern '{pattern}'")

    Vnorm_list, E_list, M_list = [], [], []
    paths_kept: list[Path] = []
    for p in outs:
        s = extract_scale_from_name(p.stem)
        E, M = _parse_energy_mag_from_out(p)
        if E is None:
            print(f"[skip] {p.name}: no '! total energy' block found")
            continue
        Vnorm_list.append(s**3)
        E_list.append(E)
        M_list.append(M if M is not None else np.nan)
        paths_kept.append(p)

    if len(Vnorm_list) < 3:
        raise RuntimeError("Need at least 3 finished outputs for fitting.")

    return np.array(Vnorm_list), np.array(E_list), np.array(M_list), paths_kept

# ============================================================
#   2. Fit and compute bulk modulus (in Ry/V₀)
# ============================================================

def fit_quadratic(V: np.ndarray, E: np.ndarray) -> np.poly1d:
    """Fit E(V) = aV² + bV + c."""
    coeffs = np.polyfit(V, E, 2)
    return np.poly1d(coeffs)

def bulk_modulus_from_poly(poly: np.poly1d) -> float:
    """Bulk modulus in Ry/V₀ units (since V normalized by V₀)."""
    a = poly.coeffs[0]
    return 2.0 * a  # V0 = 1

# ============================================================
#   3. Plot and report
# ============================================================

def plot_EV(V: np.ndarray, E: np.ndarray, poly: np.poly1d, out: str, display: bool = False):
    """Plot E(V/V₀) and quadratic fit, annotate vertex form and bulk modulus."""
    V_line = np.linspace(V.min(), V.max(), 200)
    E_line = poly(V_line)

    a = poly.coeffs[0]
    b = -poly.coeffs[1] / (2 * a)
    c = poly(b)
    B = 2 * a  # Ry / V0

    formula = fr"$E(V) = {a:.3e}(V - {b:.3f})^2 + {c:.6f}$" + "\n" + fr"$B = 2a = {B:.3e}$ Ry/V₀"

    plt.figure(figsize=(6, 4))
    plt.scatter(V, E, color="blue", label="data", zorder=3)
    plt.plot(V_line, E_line, color="red", label="fit", zorder=2)
    plt.xlabel(r"Volume ($V/V_0$)")
    plt.ylabel(r"Total Energy (Ry)")
    plt.title("E(V) Fit and Bulk Modulus")
    plt.legend()
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.text(
        0.05, 0.95, formula,
        transform=plt.gca().transAxes,
        fontsize=9,
        va="top", ha="left",
        bbox=dict(facecolor="white", alpha=0.8, edgecolor="none")
    )
    plt.tight_layout()
    plt.savefig(out, dpi=300)
    if display:
        plt.show()
    plt.close()

def plot_MV(V: np.ndarray, M: np.ndarray, out: str, display: bool = False):
    """Plot total magnetization vs normalized volume."""
    plt.figure(figsize=(6, 4))
    plt.scatter(V, M, color="purple", marker="o")
    plt.plot(np.sort(V), np.array(M)[np.argsort(V)], color="black", lw=1)
    plt.xlabel(r"Volume ($V/V_0$)")
    plt.ylabel(r"Total Magnetization (Bohr/cell)")
    plt.title("Magnetization vs Volume")
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.tight_layout()
    plt.savefig(out, dpi=300)
    if display:
        plt.show()
    plt.close()

def magnetization_at_V0(V: np.ndarray, M: np.ndarray, V0: float, window: float = 0.03):
    """
    Estimate magnetization at equilibrium volume V0.
    Performs a linear fit M(V) within ±window of V0 (default ±3% range).
    Returns (M(V0), slope, intercept).
    """
    mask = (V >= V0 * (1 - window)) & (V <= V0 * (1 + window))
    if mask.sum() < 2:
        mask[:] = True  # fallback if too few points
    coeffs = np.polyfit(V[mask], M[mask], 1)
    M0 = np.polyval(coeffs, V0)
    return M0, coeffs[0], coeffs[1]

# ============================================================
#   4. Main entry for CLI
# ============================================================


def analyze_bulk_modulus(pattern: str = "a*_scf.out", save_png: str = "bulk_EV.png",
                         display: bool = False, plot_magvol: bool = False):
    """
    Fit E(V/V₀) from QE outputs (using filename scales), and compute bulk modulus in Ry/V₀.
    If plot_magvol=True, also plot magnetization vs volume.
    """
    Vnorm, E, M, paths = read_energy_magnetization(pattern)
    poly = fit_quadratic(Vnorm, E)
    a, b, c = poly.coeffs
    V0 = -b / (2 * a)
    E0 = poly(V0)
    B = 2 * a

    print("Files used:")
    for p in paths:
        print(f"  {p.name}")
    print("\nFit: E(V) = aV² + bV + c")
    print(f"  a = {a:.6e}  b = {b:.6e}  c = {c:.6e}")
    print(f"  V₀ = {V0:.6f}  (normalized)")
    print(f"  E₀ = {E0:.8f} Ry")
    print(f"  B  = {B:.6e}  Ry / V₀")

    plot_EV(Vnorm, E, poly, save_png, display)
    print(f"Saved E–V plot: {save_png}")

    # ============================================================
    # Save raw E(V) and magnetization data to CSV
    # ============================================================
    csv_path = Path(save_png).with_suffix("").with_name("bulk_EV_data.csv")

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Vnorm", "Energy_Ry", "Magnetization_Bohr", "Filename"])
        writer.writerows(
            [vnorm, energy, magnetization, path.name]
            for vnorm, energy, magnetization, path in zip(Vnorm, E, M, paths)
        )
    print(f"Saved raw E–V data → {csv_path}")

    if plot_magvol:
        # --- Magnetization at equilibrium ---
        M0, slope, intercept = magnetization_at_V0(Vnorm, M, V0)
        print(f"\nGround-state magnetization M(V₀) = {M0:.4f} Bohr/cell "
            f"(linear fit slope dM/dV = {slope:.4f})")
        mv_png = Path(save_png).with_name("bulk_MV.png")
        plot_MV(Vnorm, M, mv_png, display)

        # optional marker for M(V0)
        plt.figure(figsize=(6, 4))
        plt.scatter(Vnorm, M, color="purple", marker="o")
        plt.plot(np.sort(Vnorm), np.array(M)[np.argsort(Vnorm)], color="black", lw=1)
        plt.axvline(V0, color="red", ls="--", lw=1)
        plt.scatter([V0], [M0], color="red", zorder=5)
        plt.text(V0, M0, f"  M(V₀)={M0:.3f}", color="red", va="bottom", ha="left")
        plt.xlabel(r"Volume ($V/V_0$)")
        plt.ylabel(r"Total Magnetization (Bohr/cell)")
        plt.title("Magnetization vs Volume")
        plt.grid(True, linestyle="--", alpha=0.5)
        plt.tight_layout()
        mv_marked = Path(save_png).with_name("bulk_MV_marked.png")
        plt.savefig(mv_marked, dpi=300)
        if display:
            plt.show()
        plt.close()
        print(f"Saved M–V plot with M(V₀): {mv_marked}")
