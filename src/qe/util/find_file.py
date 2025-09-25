import glob
import os
import warnings

def find_local(pattern: str, cwd: str = ".") -> list[str]:
    """Return all matches for pattern in `cwd`."""
    return glob.glob(os.path.join(cwd, pattern))

def search_siblings(pattern: str, cwd: str = ".") -> list[str]:
    """Return all matches for sibling directories of `cwd` for files matching `pattern`."""
    cwd = os.path.abspath(cwd)
    parent = os.path.dirname(cwd)
    matches = []
    for sub in os.listdir(parent):
        subdir = os.path.join(parent, sub)
        if os.path.isdir(subdir):
            matches.extend(glob.glob(os.path.join(subdir, pattern)))
    return matches


def resolve_file(
    name: str,
    pattern: str,
    search_sibling_file: bool = False,
    allow_multi: bool = False,
    cwd: str = ".",
) -> str:
    """
    Resolver for input files.

    Resolution order:
    1. Try current directory with glob `pattern`.
    2. If not found and `search_sibling_file` is set,
       look for that filename in sibling directories.

    Parameters
    ----------
    name : str
        Friendly name for error messages (e.g. "nscf.out").
    pattern : str
        Glob pattern (e.g. "*.pdos_tot", "nscf.in").
    search_sibling_file : bool
        look for sibling dirs if not found locally.
    allow_multi : bool
        - False: raise if multiple matches found.
        - True: return the first match.
    cwd : str
        Directory to search in (default: ".").

    Returns
    -------
    str
        Path to resolved file.

    Raises
    ------
    FileNotFoundError
        If no match found.
    RuntimeError
        If multiple matches found and allow_multi=False.
    """
    # Step 1: local search
    matches = find_local(pattern, cwd)
    if matches:
        if len(matches) > 1:
            if not allow_multi:
                raise RuntimeError(
                    f"Multiple {name} found in {cwd}: {matches}. "
                    f"Specify explicitly with --{name.replace('.', '-')}"
                )
            warnings.warn(
                f"Multiple {name} found in {cwd}. "
                f"Using first match: {matches[0]}"
                f"Specify explicitly with --{name.replace('.', '-')}",
                RuntimeWarning,
                stacklevel=2,
            )
        return matches[0]

    # Step 2: sibling search
    if search_sibling_file:
        sib_matches = search_siblings(pattern, cwd)
        if sib_matches:
            if len(sib_matches) > 1:
                if not allow_multi:
                    raise RuntimeError(
                        f"Multiple {name} found in sibling dirs: {sib_matches}. "
                        f"Specify explicitly with --{name.replace('.', '-')}"
                    )
                warnings.warn(
                    f"Multiple {name} found in sibling dirs. "
                    f"Using first match: {sib_matches[0]}"
                    f"Specify explicitly with --{name.replace('.', '-')}",
                    RuntimeWarning,
                    stacklevel=2,
                )
            return sib_matches[0]

    # Step 3: not found
    raise FileNotFoundError(f"Could not resolve {name} (pattern={pattern})")