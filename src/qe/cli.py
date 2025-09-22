import argparse
from .convert import in2xsf
from .plot import plot_dos, plot_band

def main():
    parser = argparse.ArgumentParser(
        prog="qe",
        description="Quantum ESPRESSO utilities"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # --- convert_xsf ---
    p_xsf = subparsers.add_parser("in2xsf", help="Convert QE input (*.in) to XSF")
    p_xsf.add_argument("scf_in", help="Input QE .in file (e.g. scf.in, nscf.in, relax.in)")
    p_xsf.add_argument("-o", "--output", help="Optional output XSF filename")
    p_xsf.set_defaults(func=lambda args: in2xsf(args.scf_in, args.output))

    # --- plot_dos ---
    p_dos = subparsers.add_parser("plot_dos", help="Plot total DOS and optional PDOS")
    p_dos.add_argument("--pdos-tot", help="Path to total DOS file (pdos_tot)")
    p_dos.add_argument("--nscf-in", help="Path to nscf.in")
    p_dos.add_argument("--nscf-out", help="Path to nscf.out")
    p_dos.add_argument("--pdos-files", help="Comma-separated pdos files (e.g. Au.pdos_atm#1(Au)_wfc#1(s))")
    p_dos.add_argument("--group", help="Comma-separated grouping keys (orb, elem, site)")
    p_dos.add_argument("--save-png", help="Save figure to file (default: <prefix>_dos.png)")
    p_dos.add_argument("--display", action="store_true", help="Show plot interactively instead of saving")
    p_dos.add_argument("--xlim",
        nargs=2,
        type=float,
        default=(-8.0, 7.0),
        metavar=("XMIN", "XMAX"),
        help="Energy window relative to E_F (default: -8 7)"
    )
    p_dos.set_defaults(func=lambda args: plot_dos(
        pdos_tot=args.pdos_tot,
        nscf_in=args.nscf_in,
        nscf_out=args.nscf_out,
        pdos_files=args.pdos_files.split(",") if args.pdos_files else None,
        group_keys=args.group.split(",") if args.group else None,
        save_png=args.save_png,
        display=args.display,
        xlim=args.xlim
    ))

    # --- plot_band ---
    p_band = subparsers.add_parser("plot_band", help="Plot electronic band structure")
    p_band.add_argument("--band-in", help="Path to band.in (K-path definition)")
    p_band.add_argument("--bands-in", help="Comma-separated bands input files (e.g. bands_up.in). ")
    p_band.add_argument("--nscf-out", help="Path to nscf.out (for Fermi energy)")
    p_band.add_argument("--save-png", help="Save figure to file (default: <prefix>_band.png)")
    p_band.add_argument("--display", action="store_true", help="Show plot interactively instead of saving")
    p_band.add_argument("--ylim",
        nargs=2,
        type=float,
        default=(-8.0, 7.0),
        metavar=("YMIN", "YMAX"),
        help="Energy window relative to E_F (default: -8 7)"
    )
    p_band.set_defaults(func=lambda args: plot_band(
        band_in=args.band_in,
        bands_in=args.bands_in.split(",") if args.bands_in else None,
        nscf_out=args.nscf_out,
        save_png=args.save_png,
        display=args.display,
        ylim=args.ylim,
    ))

    # --- plot-bands ---


    # --- parse + dispatch ---
    args = parser.parse_args()
    args.func(args)