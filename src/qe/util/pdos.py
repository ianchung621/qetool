import re
import numpy as np
from pathlib import Path
from collections import defaultdict

def read_nspin(nscf_in: str) -> int:
    with open(nscf_in) as f:
        text = f.read().lower()
    match = re.search(r"nspin\s*=\s*(\d+)", text)
    return int(match.group(1)) if match else 1


def read_fermi(nscf_out: str) -> float:
    with open(nscf_out) as f:
        for line in f:
            if "the fermi energy is" in line.lower():
                return float(line.split()[-2])  # "is XXX ev"
    raise ValueError("Fermi energy not found in output.")


def load_dos(pdos_tot: str) -> np.ndarray:
    return np.loadtxt(pdos_tot)

class PDOSMeta:
    """Metadata parsed from QE PDOS filename."""
    def __init__(self, site_idx: int, elem: str, wf_idx: int, orb: str):
        self.site_idx = site_idx
        self.elem = elem
        self.wf_idx = wf_idx
        self.orb = orb


def parse_pdos_filename(fn: str) -> PDOSMeta:
    """
    Parse QE PDOS filename like:
    Fe.pdos_atm#1(Fe)_wfc#3(p)

    Returns PDOSMeta(site_idx, elem, wf_idx, orb)
    """
    name = Path(fn).name
    m = re.search(r"atm#(\d+)\((\w+)\)_wfc#(\d+)\((\w)\)", name)
    if not m:
        raise ValueError(f"Cannot parse PDOS filename: {fn}")
    site_idx, elem, wf_idx, orb = m.groups()
    return PDOSMeta(int(site_idx), elem, int(wf_idx), orb)


def make_key(meta: PDOSMeta, group_keys: list[str]):
    """
    Build group key tuple from PDOSMeta and requested grouping fields.
    Example: group_keys=["orb","elem"] -> ("p","Fe")
    """
    parts = []
    for k in group_keys:
        if k == "elem":
            parts.append(meta.elem)
        elif k == "site":
            parts.append(meta.site_idx)
        elif k == "orb":
            parts.append(meta.orb)
        else:
            raise ValueError(f"Unknown group key: {k}, supported: elem, site, orb")
    return tuple(parts)

def load_and_group_pdos(
    pdos_files: list[str],
    nspin: int,
    group_keys: list[str],
):
    """
    Load QE PDOS files and group by keys.

    Parameters
    ----------
    pdos_files : list[str]
        Paths to PDOS files.
    nspin : int
        Spin setting (1 or 2).
    efermi : float
        Fermi level.
    group_keys : list[str]
        Fields to group by (orb, elem, site).

    Returns
    -------
    grouped : dict
        {key: (energies, dos)} where
        - dos has shape (N,) if nspin=1
        - dos has shape (N, 2) if nspin=2
    """
    grouped = defaultdict(lambda: None)

    for fn in pdos_files:
        meta = parse_pdos_filename(fn)
        key = make_key(meta, group_keys)
        data = np.loadtxt(fn)
        energies = data[:, 0]

        if nspin == 1:
            dos = data[:, 1]
        elif nspin == 2:
            dos = data[:, 1:3]
        else:
            raise NotImplementedError("nspin=4 not supported")

        if grouped[key] is None:
            grouped[key] = (energies, dos.copy())
        else:
            grouped[key] = (energies, grouped[key][1] + dos)

    return grouped

def format_label(key: tuple, group_keys: list[str]) -> str:
    """
    Format grouped PDOS label.

    Rules
    -----
    - If 'elem' in group_keys: include element symbol.
    - If 'site' in group_keys: append site index to element (e.g. Fe1).
    - If 'orb' in group_keys: append orbital after element/site (e.g. Fe1-d).
    - If only orb: label is just 's', 'p', 'd'.
    """
    parts = dict(zip(group_keys, key))

    label = ""
    if "elem" in parts:
        label += parts["elem"]
        if "site" in parts:
            label += str(parts["site"])
    elif "site" in parts:
        # no element, just site index
        label += f"site{parts['site']}"

    if "orb" in parts:
        if label:
            label += f" - {parts['orb']}"
        else:
            label = parts["orb"]

    return label