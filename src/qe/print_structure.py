from typing import Literal
import numpy as np

def format_array(arr: np.ndarray, precision: int = 9, sep: str = "    ") -> str:
    """Return array values as a string with fixed precision, no brackets."""
    return sep.join(f"{x:.{precision}f}" for x in arr.ravel())

def print_cell_param(*vectors: np.ndarray|list):
    print('cell param:')
    for v in vectors:
        if isinstance(v, list):
            v = np.array(v)
        print("    ", format_array(v))

def print_cell_by_structure(
    structure: Literal["sc","fcc","bcc","hcp"],
    a: float,
    b: float = None,
    c: float = None):
    if b is None:
        b = a
    if c is None:
        c = a
    
    if structure == "sc":  # simple cubic
        a1 = np.array([a, 0, 0])
        a2 = np.array([0, b, 0])
        a3 = np.array([0, 0, c])

    elif structure == "fcc":  # face-centered cubic (primitive)
        a1 = a * np.array([0, 0.5, 0.5])
        a2 = b * np.array([0.5, 0, 0.5])
        a3 = c * np.array([0.5, 0.5, 0])

    elif structure == "bcc":  # body-centered cubic (primitive)
        a1 = 0.5 * a * np.array([-1, 1, 1])
        a2 = 0.5 * b * np.array([1, -1, 1])
        a3 = 0.5 * c * np.array([1, 1, -1])

    elif structure == "hcp":  # hexagonal close-packed (primitive)
        a1 = a * np.array([1, 0, 0])
        a2 = a * np.array([-0.5, np.sqrt(3)/2, 0])
        a3 = c * np.array([0, 0, 1])

    else:
        raise ValueError(f"Unknown structure type: {structure}")

    print_cell_param(a1, a2, a3)

def print_atom_pos(atoms: list[str], vectors: list[np.ndarray|list]):
    print('atom pos:')
    for a, v in zip(atoms, vectors):
        if isinstance(v, list):
            v = np.array(v)
        print("    " ,a, format_array(v))