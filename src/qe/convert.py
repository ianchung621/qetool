from pathlib import Path
import re

import numpy as np
from .util.read_qe import read_prefix


def _require_ase_io():
    try:
        from ase.io import read, write
    except ImportError as exc:
        raise ImportError(
            "The XSF conversion commands require ASE. Install it with "
            "`pip install 'qetool[ase] @ git+https://github.com/ianchung621/qetool.git'`, "
            "`pip install '.[ase]'` from this repo, or `pip install ase`."
        ) from exc
    return read, write

def in2xsf(fn: str, out: str | None = None) -> str:
    """
    Convert Quantum ESPRESSO input file (*.in) to XSF format.
    
    Parameters
    ----------
    fn : str
        Path to the QE input file (e.g., scf.in, nscf.in).
    out : str | None, default=None
        Output filename. If None, automatically derived from input.
    """
    read, write = _require_ase_io()
    atoms = read(fn, format="espresso-in")
    in_path = Path(fn)

    if out is None:
        out_path = read_prefix(in_path) + ".xsf"
    else:
        out_path = Path(out)

    write(out_path, atoms, format="xsf")
    print(f"xsf is written to {out_path}")


def _parse_last_moment_block(out_path: str, nat_expected: int | None = None) -> list[float]:
    """
    Parse the *last* 'Magnetic moment per site' block in a QE output.
    Returns a list of magnitudes (μB) ordered by atom index.
    """
    hdr = re.compile(r"^\s*Magnetic moment per site", re.I)
    row = re.compile(r"^\s*atom\s+(\d+).+?magn=\s*([-+]?\d+(?:\.\d+)?)", re.I)
    moments_last = None
    with open(out_path, "r", encoding="utf-8", errors="ignore") as f:
        collecting = False
        moments_tmp: dict[int, float] = {}
        for line in f:
            if hdr.search(line):
                collecting = True
                moments_tmp = {}
                continue
            if collecting:
                m = row.search(line)
                if m:
                    idx = int(m.group(1))  # 1-based
                    val = float(m.group(2))
                    moments_tmp[idx] = val
                else:
                    # end of block
                    if moments_tmp:
                        # convert to list in index order
                        max_idx = max(moments_tmp)
                        arr = [moments_tmp.get(i, 0.0) for i in range(1, max_idx + 1)]
                        moments_last = arr
                    collecting = False
        # also commit if file ends within a block
        if collecting and moments_tmp:
            max_idx = max(moments_tmp)
            moments_last = [moments_tmp.get(i, 0.0) for i in range(1, max_idx + 1)]

    if moments_last is None:
        raise RuntimeError(f"No 'Magnetic moment per site' block found in {out_path}")

    if nat_expected is not None and len(moments_last) != nat_expected:
        # Some outputs print fewer rows (e.g., only magnetic species); pad with zeros
        if len(moments_last) < nat_expected:
            moments_last = moments_last + [0.0] * (nat_expected - len(moments_last))
        else:
            moments_last = moments_last[:nat_expected]
    return moments_last

def _normalize(v: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(v)
    if n == 0:
        return v
    return v / n

def _write_xsf_manual(cell: np.ndarray, Z: np.ndarray, pos: np.ndarray,
                      vectors: np.ndarray, xsf_path: str) -> str:
    """
    Minimal XSF writer. Stores 'vectors' in the PRIMCOORD trailing 3 columns.
    """
    assert cell.shape == (3, 3)
    assert pos.shape[1] == 3
    assert vectors.shape == pos.shape
    nat = len(Z)
    with open(xsf_path, "w", encoding="utf-8") as f:
        f.write("CRYSTAL\n")
        f.write("PRIMVEC\n")
        for v in cell:
            f.write(f"  {v[0]:.9f}  {v[1]:.9f}  {v[2]:.9f}\n")
        f.write("PRIMCOORD\n")
        f.write(f"{nat} 1\n")
        for i in range(nat):
            f.write(f"{int(Z[i]):3d}  {pos[i,0]:.9f}  {pos[i,1]:.9f}  {pos[i,2]:.9f}"
                    f"   {vectors[i,0]:.6f}  {vectors[i,1]:.6f}  {vectors[i,2]:.6f}\n")
    return xsf_path

def inout2xsf(scf_in: str, scf_out: str, out: str | None = None,
              axis: tuple[float, float, float] = (0.0, 0.0, 1.0)) -> str:
    """
    Convert QE scf.in + scf.out → XSF with magnetic moments as arrows (manual writer).

    - Moments are read from the *last* 'Magnetic moment per site' block in scf.out.
    - Arrows point along 'axis' with length = |moment| in μB (sign => direction).

    Parameters
    ----------
    scf_in : str
    scf_out : str
    out : str | None
    axis : tuple[float,float,float]
    """
    read, _ = _require_ase_io()
    out_path = Path(out) if out else Path(read_prefix(scf_in) + ".xsf")
    in_path = Path(scf_in)

    atoms = read(in_path, format="espresso-in")
    nat = len(atoms)
    moments = _parse_last_moment_block(scf_out, nat_expected=nat)  # μB
    axis_v = _normalize(np.array(axis, dtype=float))

    vecs = np.outer(np.array(moments, dtype=float), axis_v)  # (nat,3)
    cell = np.array(atoms.cell.array, dtype=float)
    pos = atoms.get_positions()
    Z = atoms.get_atomic_numbers()

    _write_xsf_manual(cell, Z, pos, vecs, str(out_path))
    print(f"[qe] XSF (with moment arrows) written to {out_path}")
    return str(out_path)
