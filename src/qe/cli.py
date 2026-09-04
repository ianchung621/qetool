import argparse
from pathlib import Path

from .convert import in2xsf, inout2xsf
from .plot import plot_dos, plot_band
from .bulk_modulus import prepare_scaled_inputs, analyze_bulk_modulus
from .opt_cond import plot_conductivity
from .dielectric import plot_dielectric
from .kerr_rotation import plot_kerr_rotation
from .phonon import plot_phonon_band, plot_phonon_dos, plot_a2f

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

    # --- plot_opt (optical conductivity) ---
    p_opt = subparsers.add_parser("plot_opt", help="Plot optical conductivity from postw90 (kubo)")
    p_opt.add_argument("component", help="Tensor component, e.g. S_xx, S_xy, A_xy")
    p_opt.add_argument("--prefix", help="Wannier seedname (default: infer from *.win)")
    p_opt.add_argument(
        "--unit",
        choices=["S/cm", "S/m", "s^-1"],
        default="S/cm",
        help="Output unit for optical conductivity"
    )
    p_opt.add_argument("--jdos", action="store_true", help="Overlay JDOS on secondary axis")
    p_opt.add_argument("--soc", action="store_true", help="SOC or magnetic calculation (no spin degeneracy factor)")
    p_opt.add_argument("--save-png", help="Save figure to file (default: <prefix>_opt_cond_<component>.png)")
    p_opt.add_argument("--display", action="store_true", help="Show plot interactively instead of saving")
    p_opt.set_defaults(
        func=lambda args: plot_conductivity(
            component=args.component,
            prefix=args.prefix,
            jdos=args.jdos,
            out_unit=args.unit,
            save_png=args.save_png,
            display=args.display,
            soc=args.soc,
        )
    )

    # --- plot_die (dielectric function) ---
    p_die = subparsers.add_parser("plot_die", help="Plot dielectric function ε(ω) from optical conductivity")
    p_die.add_argument("--component", default="S_xx", help="Conductivity component used for ε (default: S_xx)")
    p_die.add_argument("--prefix", help="Wannier seedname (default: infer from *.win)")
    p_die.add_argument("--eps-inf", type=float, default=1.0, help="High-frequency dielectric constant ε∞ (default: 1.0)")
    p_die.add_argument("--soc", action="store_true", help="SOC or magnetic calculation (no spin degeneracy factor)")
    p_die.add_argument("--save-png", help="Save figure to file (default: <prefix>_dielectric_<component>.png)")
    p_die.add_argument("--display", action="store_true", help="Show plot interactively instead of saving")
    p_die.set_defaults(
        func=lambda args: plot_dielectric(
            component=args.component,
            prefix=args.prefix,
            eps_inf=args.eps_inf,
            save_png=args.save_png,
            display=args.display,
            soc=args.soc,
        )
    )

    # --- plot_kerr ---
    p_kerr = subparsers.add_parser("plot_kerr", help="Plot Kerr rotation and ellipticity from Kubo conductivity")
    p_kerr.add_argument("--prefix", help="File prefix for Kubo output (expects {prefix}-kubo_S_xx.dat and -kubo_A_xy.dat)")
    p_kerr.add_argument("--unit", choices=["deg", "rad"], default="deg", help="Angle unit (default: deg)")
    p_kerr.add_argument("--save-png", help="Save figure to file (default: <prefix>_kerr.png)")
    p_kerr.add_argument("--display", action="store_true", help="Show plot interactively instead of saving")
    p_kerr.add_argument("--flip-sign", action="store_false", help="Flip sign of rotation angle to match experiment convention")
    p_kerr.set_defaults(
        func=lambda args: plot_kerr_rotation(
            prefix=args.prefix,
            unit=args.unit,
            save_png=args.save_png,
            display=args.display,
            flip_sign=args.flip_sign
        )
    )

    # --- plot_phonon_band ---
    p_ph_band = subparsers.add_parser("plot_phonon_band", help="Plot phonon dispersion from <prefix>.freq.gp")
    p_ph_band.add_argument("--prefix", help="Calculation prefix (defaults: infer from *.freq)")
    p_ph_band.add_argument("--freq-gp", help="Path to <prefix>.freq.gp (default: <prefix>.freq.gp)")
    p_ph_band.add_argument("--band-in", default="matdyn.in", help="Path to matdyn.in (default: matdyn.in)")
    p_ph_band.add_argument("--high-sym", default="high_sym.txt", help="Path to high_sym.txt (default: high_sym.txt)")
    p_ph_band.add_argument(
        "--unit",
        default="Thz",
        choices=["cm^-1", "eV", "Thz", "meV"],
        help="Frequency/energy unit for y-axis (default: Thz)"
    )
    p_ph_band.add_argument("--save-png", help="Save figure to file (default: <prefix>_phonon_band.png)")
    p_ph_band.add_argument("--display", action="store_true", help="Show plot interactively instead of saving")
    p_ph_band.set_defaults(func=lambda args: plot_phonon_band(
        prefix=args.prefix,
        freq_gp=args.freq_gp,
        band_in=args.band_in,
        high_sym=args.high_sym,
        unit=args.unit,
        save_png=args.save_png,
        display=args.display,
    ))

    # --- plot_phonon_dos ---
    p_ph_dos = subparsers.add_parser("plot_phonon_dos", help="Plot phonon DOS from <prefix>.phonon.dos")
    p_ph_dos.add_argument("--prefix", help="Calculation prefix (defaults: infer from *.phonon.dos)")
    p_ph_dos.add_argument("--phonon-dos", help="Path to <prefix>.phonon.dos")
    p_ph_dos.add_argument(
        "--energy-unit",
        default="meV",
        choices=["cm^-1", "eV", "Thz", "meV"],
        help="Energy unit for x-axis (default: meV)"
    )
    p_ph_dos.add_argument("--save-png", help="Save figure to file (default: <prefix>_phonon_dos.png)")
    p_ph_dos.add_argument("--display", action="store_true", help="Show plot interactively instead of saving")
    p_ph_dos.set_defaults(func=lambda args: plot_phonon_dos(
        prefix=args.prefix,
        phonon_dos=args.phonon_dos,
        energy_unit=args.energy_unit,
        save_png=args.save_png,
        display=args.display,
    ))

    # --- plot_a2f ---
    p_a2f = subparsers.add_parser("plot_a2f", help="Plot phonon DOS + a2F(w) from <prefix>.phonon.dos.a2F")
    p_a2f.add_argument("--prefix", help="Calculation prefix (defaults: infer from *.phonon.dos.a2F)")
    p_a2f.add_argument(
        "--energy-unit",
        default="meV",
        choices=["cm^-1", "eV", "Thz", "meV"],
        help="Energy unit for x-axis (default: meV)"
    )
    p_a2f.add_argument("--save-png", help="Save figure to file (default: <prefix>_a2f.png)")
    p_a2f.add_argument("--display", action="store_true", help="Show plot interactively instead of saving")
    p_a2f.set_defaults(func=lambda args: plot_a2f(
        prefix=args.prefix,
        energy_unit=args.energy_unit,
        save_png=args.save_png,
        display=args.display,
    ))


    # --- parse + dispatch ---
    args = parser.parse_args()
    args.func(args)