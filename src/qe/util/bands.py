import glob
import re
import os
import numpy as np

def discover_band_inputs(nspin: int, cwd: str = ".") -> list[str]:
    """Discover bands*.in files for plotting."""
    patterns = ["bands.in", "*bands*.in"]
    matches = []
    for pat in patterns:
        matches.extend(glob.glob(os.path.join(cwd, pat)))
    matches = sorted(set(matches))

    if not matches:
        raise FileNotFoundError(f"No bands*.in found in {cwd}")

    if nspin == 1:
        return [matches[0]]
    elif nspin == 2:
        if len(matches) < 2:
            raise RuntimeError(f"Expected 2 bands*.in files for spin=2, found {matches}")
        if len(matches) > 2:
            raise RuntimeError(f"Too many bands*.in files for spin=2, found {matches}")
        return matches
    elif nspin == 4:
        raise NotImplementedError
    else:
        raise ValueError(f"Unsupported nspin={nspin}")

def read_kpoints(band_in: str) -> list[tuple[str, int]]:
    """
    Parse high-symmetry k-points from band.in.

    Returns
    -------
    list of (label, index)
        Each entry is a high-symmetry label and the cumulative
        number of points up to (and including) that label.

    Example
    -------
    band.in contains:
        K_POINTS crystal_b
        4
        0.0 0.0 0.0 20  ! G
        0.5 0.0 0.0 20  ! X
        0.5 0.5 0.0 20  ! M
        0.0 0.0 0.0 20  ! G

    Output:
        [('G', 0), ('X', 20), ('M', 40), ('G', 60)]
    """
    kpoints: list[tuple[str, int]] = []

    with open(band_in) as f:
        lines = [ln.strip() for ln in f if ln.strip()]

    # find K_POINTS block
    try:
        start = next(i for i, ln in enumerate(lines) if ln.upper().startswith("K_POINTS"))
    except StopIteration:
        raise ValueError(f"No K_POINTS block found in {band_in}")

    npts = int(lines[start + 1])
    block = lines[start + 2 : start + 2 + npts]

    cum = 0
    for row in block:
        parts = row.split("!")
        fields = parts[0].split()
        nk = int(fields[3])  # number of interpolated points
        label = parts[1].strip() if len(parts) > 1 else ""
        kpoints.append((label, cum))
        cum += nk

    return kpoints


def parse_bands_in(bands_in: str) -> tuple[str | None, int | None]:
    """
    Extract filband and spin_component from bands.in.
    """
    filband = None
    spin_comp = None
    with open(bands_in) as f:
        for line in f:
            if "filband" in line.lower():
                m = re.search(r"filband\s*=\s*['\"]([^'\"]+)['\"]", line, re.IGNORECASE)
                if m:
                    filband = m.group(1).strip()
            if "spin_component" in line.lower():
                m = re.search(r"spin_component\s*=\s*(\d+)", line, re.IGNORECASE)
                if m:
                    spin_comp = int(m.group(1))
    return filband, spin_comp


def load_band_data(filband: str) -> np.ndarray:
    """
    Load QE band data from .gnu or .dat file.
    Returns array shape (n_points, n_bands+1):
      col0 = k-distance, cols1.. = band energies
    """
    blocks: list[np.ndarray] = []
    current_block = []
    with open(filband) as f:
        for line in f:
            line = line.strip()
            if not line:
                if current_block:
                    blocks.append(np.array(current_block, float))
                    current_block = []
                continue
            current_block.append(line.split())
        if current_block:
            blocks.append(np.array(current_block, float))

    # stack blocks into (n_points, n_bands+1)
    n_bands = len(blocks)
    n_points = blocks[0].shape[0]
    arr = np.zeros((n_points, n_bands + 1), float)
    arr[:, 0] = blocks[0][:, 0]  # k distances
    for i, b in enumerate(blocks, start=1):
        arr[:, i] = b[:, 1]       # energy
    return arr


def format_kpoints(kpoints: list[tuple[str, int]], k_val: np.ndarray) -> tuple[list[float], list[str]]:
    """
    Convert (label, cumulative k-point count) into xticks and labels.
    """
    label_map = {"G": "Γ"}

    for lbl, d in kpoints:
        if d >= len(k_val):
            raise ValueError(
                f"Label '{lbl}' refers to index {d}, but k_val has length {len(k_val)}.\n"
                "This usually happens because QE reduced symmetry in the band calculation.\n\n"
                "To fix this, rerun with:\n"
                "  - in band.in:   nosym = .true., noinv = .true. inside &system\n"
                "  - in bands.in:  lsym = .false.\n"
            )

    xticks = [k_val[d] for _, d in kpoints]
    xlabels = [label_map.get(lbl, lbl) if lbl else "" for lbl, _ in kpoints]
    return xticks, xlabels