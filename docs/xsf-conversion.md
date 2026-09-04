# XSF Conversion

The XSF commands convert QE inputs to XCrySDen-compatible `.xsf` files. They require ASE, which is optional for the package.

Install with ASE support:

```bash
pip install -e '.[ase]'
```

## Suggested Folder Structure

```text
material/
  01-SCF/
    scf.in
    scf.out
    Material.xsf
```

## `qe in2xsf`

Converts a QE input file to XSF.

```bash
qe in2xsf scf.in
```

Custom output:

```bash
qe in2xsf scf.in --output Material.xsf
```

### Flags

| Flag | Meaning |
| --- | --- |
| `scf_in` | QE input file, such as `scf.in`, `nscf.in`, or `relax.in`. |
| `-o`, `--output PATH` | Output XSF path. If omitted, the command uses the `prefix` from the QE input and writes `<prefix>.xsf`. |

### Expected Input and Output

Input is a QE input file readable by ASE's `espresso-in` parser. Output is an XSF structure file readable by XCrySDen and similar visualization tools.

## `qe inout2xsf`

Converts a QE input plus output file to XSF and writes magnetic moments as arrows.

```bash
qe inout2xsf --scf_in scf.in --scf_out scf.out
```

Choose moment direction:

```bash
qe inout2xsf --scf_in scf.in --scf_out scf.out --axis 0 0 1
```

### Flags

| Flag | Meaning |
| --- | --- |
| `--scf_in PATH` | QE input file. Defaults to `scf.in` when omitted. |
| `--scf_out PATH` | QE output file. Defaults to `scf.out` when omitted. |
| `-o`, `--output PATH` | Output XSF path. If omitted, the command uses the `prefix` from the QE input and writes `<prefix>.xsf`. |
| `--axis X Y Z` | Direction used for collinear moment arrows. Default: `0 0 1`. |

### Expected Input and Output

Input `scf.in` provides cell, positions, and atomic numbers through ASE. Input `scf.out` must contain a `Magnetic moment per site` block with `magn=` values. The parser uses the last such block in the output.

Output is an XSF file with the moment vectors in the three trailing `PRIMCOORD` columns. If fewer moment rows are printed than atoms, missing atoms are padded with zero-length vectors.
