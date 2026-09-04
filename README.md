# QE Utilities

Small command-line helpers for plotting and converting Quantum ESPRESSO and Wannier90 results.

## Install

From GitHub:

```bash
pip install git+https://github.com/ianchung621/qetool.git
```

For development from a local clone:

```bash
pip install -e .
```

XSF conversion uses ASE, which is optional:

```bash
pip install 'qetool[ase] @ git+https://github.com/ianchung621/qetool.git'
```

From a local clone, use:

```bash
pip install -e '.[ase]'
```

After installation, the command is `qe`.

## Agent Skill

To help future agents use qetool inside another QE calculation repo, copy [SKILL.md](SKILL.md) to:

```text
.agents/qe-plotting/SKILL.md
```

The target environment still needs qetool installed and available on `PATH`.

## Basic Usage

Run commands from the folder that contains the relevant QE/Wannier90 output files, or pass paths explicitly.

```bash
qe plot_dos --gap
qe plot_band --gap
qe bulk_modulus --prepare
qe bulk_modulus --magvol
qe plot_opt S_xx --jdos
qe plot_die --component S_xx
qe plot_kerr
qe plot_phonon_band
qe plot_phonon_dos
qe plot_a2f
qe in2xsf scf.in
qe inout2xsf --scf_in scf.in --scf_out scf.out
```

By default, plotting commands save PNG files instead of opening a GUI window. Add `--display` to show plots interactively.

## Commands

| Command | Purpose | Detailed docs |
| --- | --- | --- |
| `plot_dos` | Plot total DOS and optional grouped PDOS | [docs/electronic-plots.md](docs/electronic-plots.md) |
| `plot_band` | Plot electronic band structures | [docs/electronic-plots.md](docs/electronic-plots.md) |
| `bulk_modulus` | Prepare scaled SCF inputs and fit E(V) | [docs/bulk-modulus.md](docs/bulk-modulus.md) |
| `plot_opt` | Plot optical conductivity from `postw90` Kubo output | [docs/optics-kerr.md](docs/optics-kerr.md) |
| `plot_die` | Convert Kubo conductivity to dielectric response | [docs/optics-kerr.md](docs/optics-kerr.md) |
| `plot_kerr` | Plot Kerr rotation and ellipticity | [docs/optics-kerr.md](docs/optics-kerr.md) |
| `plot_phonon_band` | Plot phonon dispersion | [docs/phonons.md](docs/phonons.md) |
| `plot_phonon_dos` | Plot phonon DOS | [docs/phonons.md](docs/phonons.md) |
| `plot_a2f` | Plot Eliashberg spectral function curves | [docs/phonons.md](docs/phonons.md) |
| `in2xsf`, `inout2xsf` | Convert QE inputs to XSF, optionally with moment arrows | [docs/xsf-conversion.md](docs/xsf-conversion.md) |

## Example Output

- Band: [docs/images/gaas-band.png](docs/images/gaas-band.png)
- DOS: [docs/images/al-dos.png](docs/images/al-dos.png)
- Bulk modulus: [docs/images/diamond-si-bulk-ev.png](docs/images/diamond-si-bulk-ev.png)
- Optical conductivity: [docs/images/gaas-opt-cond-sxx.png](docs/images/gaas-opt-cond-sxx.png)
- Kerr rotation: [docs/images/ni-kerr.png](docs/images/ni-kerr.png)
- Phonons: [docs/images/tc-phonon-band.png](docs/images/tc-phonon-band.png)
