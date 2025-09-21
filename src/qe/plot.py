from pathlib import Path
import glob

import matplotlib.pyplot as plt

from .util.pdos import load_and_group_pdos, format_label, read_nspin, read_fermi, load_dos
from .util.find_file import resolve_file

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
        ax.plot(energies, data[:, 1], color='k', label="total")
    elif nspin == 2:
        ax.plot(energies, data[:, 1], label="spin-up")
        ax.plot(energies, data[:, 2], label="spin-down")
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
                    ax.plot(energies_p, arr[:,1], label=f"{label} ↓")

    # --- Formatting ---
    ax.axvline(efermi, color="k", linestyle="--", lw=0.8)
    ax.set_xlabel("Energy (eV)", fontsize=14)
    ax.set_ylabel("DOS (states/eV/spin/cell)", fontsize=14)
    ax.set_title(prefix, fontsize=16)
    ax.legend(fontsize=12)

    ax.tick_params(axis="both", which="major", labelsize=12)
    if xlim:
        ax.set_xlim((efermi + xlim[0], efermi + xlim[1]))

    if display:
        plt.show()
    else:
        save_png = save_png or f"{prefix}_dos.png"
        fig.savefig(save_png, bbox_inches="tight")
        print(f"Figure saved to {save_png}")

    return fig