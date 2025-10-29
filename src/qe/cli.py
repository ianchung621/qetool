import argparse
from pathlib import Path

from .convert import in2xsf, inout2xsf
from .plot import plot_dos, plot_band
from .bulk_modulus import prepare_scaled_inputs, analyze_bulk_modulus

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

    # --- convert_xsf_with_moment ---
    p_xsfm = subparsers.add_parser("inout2xsf",help="Convert QE input (*.in) + output (*.out) to XSF with magnetic moments")
    p_xsfm.add_argument("--scf_in", help="Input QE .in file (e.g. scf.in)")
    p_xsfm.add_argument("--scf_out", help="Output QE .out file (with 'magn=' lines)")
    p_xsfm.add_argument("-o", "--output", help="Optional output XSF filename")
    p_xsfm.add_argument("--axis",
        nargs=3,
        type=float,
        default=(0.0, 0.0, 1.0),
        metavar=("X", "Y", "Z"),
        help="Moment direction (for collinear spins; default z-axis)"
    )
    p_xsfm.set_defaults(func=lambda args: inout2xsf(
        args.scf_in or "scf.in",
        args.scf_out or "scf.out",
        out=args.output,
        axis=tuple(args.axis),
    ))

    # --- plot_dos ---
    p_dos = subparsers.add_parser("plot_dos", help="Plot total DOS and optional PDOS")
    p_dos.add_argument("--pdos-tot", help="Path to total DOS file (pdos_tot)")
    p_dos.add_argument("--nscf-in", help="Path to nscf.in")
    p_dos.add_argument("--nscf-out", help="Path to nscf.out")
    p_dos.add_argument("--pdos-files", help="Comma-separated pdos files (e.g. Au.pdos_atm#1(Au)_wfc#1(s))")
    p_dos.add_argument("--group", help="Comma-separated grouping keys (orb, elem, site)")
    p_dos.add_argument("--save-png", help="Save figure to file (default: <prefix>_dos.png)")
    p_dos.add_argument("--display", action="store_true", help="Show plot interactively instead of saving")
    p_dos.add_argument("--gap", dest="show_gap", action="store_true", help="Compute and annotate band gap from total DOS")
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
        show_gap=args.show_gap,
        xlim=args.xlim
    ))

    # --- plot_band ---
    p_band = subparsers.add_parser("plot_band", help="Plot electronic band structure")
    p_band.add_argument("--band-in", help="Path to band.in (K-path definition)")
    p_band.add_argument("--bands-in", help="Comma-separated bands input files (e.g. bands_up.in). ")
    p_band.add_argument("--nscf-out", help="Path to nscf.out (for Fermi energy)")
    p_band.add_argument("--save-png", help="Save figure to file (default: <prefix>_band.png)")
    p_band.add_argument("--display", action="store_true", help="Show plot interactively instead of saving")
    p_band.add_argument("--gap", dest="show_gap", action="store_true", help="Compute and annotate band gap (↑, ↓, or total)")
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
        show_gap=args.show_gap,
    ))

    # --- bulk-modulus ---
    p_bm = subparsers.add_parser("bulk_modulus", help="Prepare scaled inputs or calculate bulk modulus")
    p_bm.add_argument("--in", dest="scf_in", default="scf.in", help="Input QE file (for prepare mode)")
    p_bm.add_argument(
        "-pp", "--prepare",
        nargs="?",
        const="0.96,0.97,0.98,0.99,1,1.01,1.02,1.03,1.04",
        default=None,
        help="Comma-separated scale factors, e.g. 0.97,0.98,0.99,1,1.01")
    p_bm.add_argument("--display", action="store_true", help="Show plot interactively")
    p_bm.add_argument("-MV", "--magvol", action="store_true",
    help="Also plot magnetization vs volume (bulk_MV.png)")
    def run_bm(args):
        if args.prepare:
            scales = [float(x) for x in args.prepare.split(",")]
            return prepare_scaled_inputs(Path(args.scf_in), scales)
        else:
            return analyze_bulk_modulus(
                display=args.display,
                plot_magvol=args.magvol
            )
    p_bm.set_defaults(func=run_bm)


    # --- parse + dispatch ---
    args = parser.parse_args()
    args.func(args)