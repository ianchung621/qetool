from dataclasses import dataclass
from typing import Literal

import numpy as np

@dataclass
class GapResult:
    gap: float               # in eV
    vbm: float               # valence band maximum (eV, rel. to Ef)
    cbm: float               # conduction band minimum (eV, rel. to Ef)
    vbm_kidx: int = None  # index of k-point for VBM (if band-structure)
    cbm_kidx: int = None  # index of k-point for CBM (if band-structure)
    is_direct: bool = None
    method: Literal["DOS", "band"] = "DOS"

    def __repr__(self):
        s = f"[{self.method}] Gap = {self.gap:.3f} eV"
        if self.method == "band":
            if self.is_direct is not None:
                s += f" ({'direct' if self.is_direct else 'indirect'})"
            s += f"\nVBM = {self.vbm:.3f} eV @ k={self.vbm_kidx}, CBM = {self.cbm:.3f} eV @ k={self.cbm_kidx}"
        else:
            s += f"\nVBM = {self.vbm:.3f} eV, CBM = {self.cbm:.3f} eV"
        s += " (related to efermi)"
        return s

def get_gap_from_dos(
    energies: np.ndarray,
    dos: np.ndarray,
    efermi: float,
    thr: float = 1e-3
) -> GapResult:
    """
    Compute the electronic band gap from total DOS data.

    Parameters
    ----------
    energies : np.ndarray
        Energy grid (eV), shape (N,).
    dos : np.ndarray
        Total density of states at each energy, shape (N,).
    efermi : float
        Fermi energy (eV).
    thr : float, optional
        DOS threshold, used to
        determine the onset of valence/conduction states.
        Default is 1e-3.

    Returns
    -------
    GapResult
        Dataclass containing bandgap (eV), VBM, and CBM relative to E_F.

    Notes
    -----
    - If DOS never crosses the threshold, a zero gap is returned.
    - Energies are internally shifted so that E_F = 0.
    """
    E = energies - efermi
    mask = dos > thr

    if not np.any(mask):
        return GapResult(gap=0.0, vbm=0.0, cbm=0.0, method="DOS")

    vbm_candidates = E[(E < 0) & mask]
    cbm_candidates = E[(E > 0) & mask]

    vbm = np.max(vbm_candidates) if vbm_candidates.size else 0.0
    cbm = np.min(cbm_candidates) if cbm_candidates.size else 0.0
    gap = max(cbm - vbm, 0.0)

    return GapResult(gap=gap, vbm=vbm, cbm=cbm, method="DOS")

def get_gap_from_bands(
    k_vals: np.ndarray,
    energies: np.ndarray,
    efermi: float,
    etol: float = 0
) -> GapResult:
    """
    Compute the electronic band gap from band-structure eigenvalues.

    Parameters
    ----------
    k_vals : np.ndarray
        1D array of k-point coordinates along the path, shape (K,).
    energies : np.ndarray
        Eigenvalues (eV) for each k-point and band, shape (K, N_bands).
    efermi : float
        Fermi energy (eV).

    Returns
    -------
    GapResult
        Dataclass with:
            - gap (float): bandgap (eV)
            - vbm, cbm (float): valence/conduction band edges (rel. to E_F)
            - vbm_kidx, cbm_kidx (int): k-point indices of VBM and CBM
            - is_direct (bool): True if direct gap, False if indirect

    Notes
    -----
    - VBM is the maximum occupied state (E <= E_F)
    - CBM is the minimum unoccupied state (E >= E_F)
    - Energies are shifted internally so that E_F = 0.
    """
    E = energies - efermi

    # Mask for valence and conduction states
    val_mask = E <= - etol
    cond_mask = E >= etol

    if not np.any(val_mask) or not np.any(cond_mask):
        return GapResult(gap=0.0, vbm=0.0, cbm=0.0, method="band")

    # VBM
    vbm_idx = np.unravel_index(np.argmax(np.where(val_mask, E, -np.inf)), E.shape)
    vbm_val = E[vbm_idx]

    # CBM
    cbm_idx = np.unravel_index(np.argmin(np.where(cond_mask, E, np.inf)), E.shape)
    cbm_val = E[cbm_idx]

    gap = max(cbm_val - vbm_val, 0.0)
    is_direct = vbm_idx[0] == cbm_idx[0]

    return GapResult(
        gap=gap,
        vbm=vbm_val,
        cbm=cbm_val,
        vbm_kidx=vbm_idx[0],
        cbm_kidx=cbm_idx[0],
        is_direct=is_direct,
        method="band",
    )