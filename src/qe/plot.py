from pathlib import Path
import glob

import numpy as np
import matplotlib.pyplot as plt

from .util.read_qe import read_nspin, read_prefix
from .util.find_file import resolve_file
from .util.pdos import load_and_group_pdos, format_label, read_fermi, load_dos
from .util.bands import discover_band_inputs, read_kpoints, parse_bands_in, load_band_data, format_kpoints
from .util.plt_util import get_visible_ylim

def plot_dos(pdos_tot: str | None = None,
    nscf_in: str | None = None, 
    nscf_out: str | None = None,
    pdos_files: list[str] | None = None,
    group_keys: list[str] | None = None,
    save_png: str | None = None,
    display: bool = False,
    xlim: tuple[float, float] | None = (-8.0, 7.0),
):
    """
    Plot Quantum ESPRESSO total DOS and optional grouped PDOS.

    Parameters
    ----------
    pdos_tot : str, optional
        Path to total DOS file (e.g. pwscf.pdos_tot).
    nscf_in : str, optional
        Path to nscf.in (used to detect nspin).
    nscf_out : str, optional
        Path to nscf.out (used to extract Fermi level).
    pdos_files : list[str], optional
        List of PDOS file paths. If None and group_keys is set,
        will auto-glob <prefix>.pdos_atm*.
    group_keys : list[str], optional
        Grouping scheme for PDOS ("orb", "elem", "site" ...).
    save_png : str, optional
        Output PNG filename. Default: <prefix>_dos.png
    display : bool, default=False
        If True, show interactively. Else save to file (HPC safe).
    """
    # --- auto-glob if not provided ---
    if pdos_tot is None:
        pdos_tot = resolve_file("pdos_tot", "*.pdos_tot")

    if nscf_in is None:
        nscf_in = resolve_file("nscf.in", "nscf.in")

    if nscf_out is None:
        nscf_out = resolve_file("nscf.out", "nscf.out")
    
    prefix = Path(pdos_tot).stem
    nspin = read_nspin(nscf_in)
    efermi = read_fermi(nscf_out)
    data = load_dos(pdos_tot)

    energies = data[:, 0]
    
    fig, ax = plt.subplots()

    # --- Total DOS ---
    if nspin == 1:
        ax.plot(energies, data[:, 1], color='k', label="total", lw = 2)
    elif nspin == 2:
        ax.plot(energies, data[:, 1], color='b', label="spin-up", lw = 2)
        ax.plot(energies, - data[:, 2], color='r', label="spin-dw", lw = 2)
    elif nspin == 4:
        raise NotImplementedError
    else:
        raise ValueError(f"Unsupported nspin={nspin}")
    
    # --- Grouped PDOS ---
    if group_keys:
        if pdos_files is None:
            pdos_files = glob.glob(f"{prefix}.pdos_atm*")
            if not pdos_files:
                print(f"[WARN] No PDOS files found for {prefix}.pdos_atm*")
        if pdos_files:
            grouped = load_and_group_pdos(
                pdos_files=pdos_files,
                nspin=nspin,
                group_keys=group_keys,
            )
            for key, (energies_p, arr) in grouped.items():
                label = format_label(key, group_keys)
                if nspin == 1:
                    ax.plot(energies_p, arr, label=label)
                elif nspin == 2:
                    ax.plot(energies_p, arr[:,0], label=f"{label} ↑")
                    ax.plot(energies_p, - arr[:,1], label=f"{label} ↓")

    # --- Formatting ---
    if efermi:
        ax.axvline(efermi, color="k", linestyle="--", lw=0.8)
    ax.set_xlabel("Energy (eV)", fontsize=14)
    ax.set_ylabel("DOS (states/eV/spin/cell)", fontsize=14)
    ax.set_title(prefix, fontsize=16)
    ax.legend(fontsize=12, loc = 'upper right')

    ax.tick_params(axis="both", which="major", labelsize=12)
    if xlim:
        ax.set_xlim((xlim[0] + efermi, xlim[1] + efermi))
    bottom, top = get_visible_ylim(ax)
    if nspin == 1:
        ax.set_ylim(bottom=0, top=top)
    elif nspin == 2:
        ax.axhline(0, color = 'k', lw = 1)
        ax.set_ylim(bottom=bottom, top=top)

    if display:
        plt.show()
    else:
        save_png = save_png or f"{prefix}_dos.png"
        fig.savefig(save_png, bbox_inches="tight")
        print(f"Figure saved to {save_png}")

def plot_band(
    band_in: str | None = None,
    bands_in: list[str] | None = None,
    nscf_out: str | None = None,
    save_png: str | None = None,
    display: bool = False,
    ylim: tuple[float, float] | None = (-8.0, 7.0),
):
    """
    Plot Quantum ESPRESSO band structure.

    Parameters
    ----------
    band_in : str, optional
        Path to band.in (K-point path definition).
    bands_in : list[str], optional
        One or two bands*.in files (spin = 1 or 2).
        If None, will auto-discover.
    nscf_out : str, optional
        Path to nscf.out (used to extract Fermi level).
    save_png : str, optional
        Output PNG filename. Default: <prefix>_band.png
    display : bool, default=False
        If True, show interactively. Else save to file (HPC safe).
    xlim : tuple[float, float], optional
        Energy axis limits relative to Fermi (default: -8, 7 eV).
    """
    COLOR_UP, COLOR_DN = "blue", "red" 
    # --- auto-glob if not provided ---
    if band_in is None:
        band_in = resolve_file("band.in", "band.in")

    if nscf_out is None:
        nscf_out = resolve_file("nscf.out", "nscf.out", search_sibling_file="nscf.out")
    
    nspin = read_nspin(band_in)

    if bands_in is None:
        bands_in = discover_band_inputs(nspin)

    # --- read metadata ---
    prefix = read_prefix(band_in)
    kpoints = read_kpoints(band_in)
    efermi = read_fermi(nscf_out)

    # --- read bands ---
    band_sources = []
    for b_in in bands_in:
        filband, spin_comp = parse_bands_in(b_in)
        if not filband:
            raise RuntimeError(f"No filband=... found in {b_in}")
        gnu_data = load_band_data(filband + ".gnu")
        band_sources.append((gnu_data, spin_comp))
    # --- plotting ---
    fig, ax = plt.subplots()

    for data, spin_comp in band_sources:
        k_vals, energies = data[:, 0], data[:, 1:]

        if nspin == 1:
            ax.plot(k_vals, energies, color="b", lw=1.0)
        elif nspin == 2 and spin_comp == 1:
            ax.plot(k_vals, energies, color=COLOR_UP, lw=1.0)
        elif nspin == 2 and spin_comp == 2:
            ax.plot(k_vals, energies, color=COLOR_DN, lw=1.0)
        else:
            ax.plot(k_vals, energies, lw=1.0)
    
    # --- format axes ---
    xticks, xlabels = format_kpoints(kpoints, k_vals)
    ax.set_xticks(xticks)
    ax.set_xticklabels(xlabels)
    ax.tick_params(axis="both", which="major", labelsize=12)
    for k_pts in xticks:
        ax.axvline(k_pts, color="k", linestyle="--", lw=0.8)
    ax.set_xlim(xticks[0], xticks[-1])

    if efermi:
        ax.axhline(efermi, color="k", linestyle=":", lw=0.8)
    ax.set_ylabel("Energy (eV)", fontsize=14)
    ax.set_title(prefix, fontsize=16)

    if ylim:
        ax.set_ylim((ylim[0] + efermi, ylim[1] + efermi))

    if nspin == 2:
        ax.plot([], [], color=COLOR_UP, label="spin-up")
        ax.plot([], [], color=COLOR_DN, label="spin-dn")
        ax.legend(fontsize=12)

    # --- save or display ---
    if display:
        plt.show()
    else:
        save_png = save_png or f"{prefix}_band.png"
        fig.savefig(save_png, bbox_inches="tight")
        print(f"Figure saved to {save_png}")