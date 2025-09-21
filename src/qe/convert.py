from pathlib import Path
from ase.io import read, write

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
    atoms = read(fn, format="espresso-in")
    in_path = Path(fn)

    if out is None:
        # If filename ends exactly with "scf.in", replace suffix with "scf.xsf"
        if in_path.name == "scf.in":
            out_path = in_path.with_suffix(".xsf")
        # For files like nscf.in, relax.in, etc → just swap ".in" → ".xsf"
        elif in_path.suffix == ".in":
            out_path = in_path.with_suffix(".xsf")
        else:
            raise ValueError(f"Unrecognized input file extension: {fn}")
    else:
        out_path = Path(out)

    write(out_path, atoms, format="xsf")
    print(f"xsf is written to {out_path}")