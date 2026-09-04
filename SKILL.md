---
name: qe-plotting
description: Use the qetool `qe` command-line utilities to quickly plot Quantum ESPRESSO and Wannier90 outputs in calculation folders. Use when working outside the qetool repo and the user wants DOS, band, bulk-modulus, optical, Kerr, phonon, a2F, or XSF outputs from existing QE/Wannier90 files.
---

# QE Plotting

Use this skill to generate plots or XSF files from existing Quantum ESPRESSO/Wannier90 calculation outputs with the `qe` CLI from qetool.

## First Checks

1. Confirm the `qe` command is available:

   ```bash
   qe --help
   ```

2. If unavailable, inspect the environment before installing. Prefer an existing module, venv, conda env, or user-local install path on HPC.

3. Install qetool if needed:

   ```bash
   pip install git+https://github.com/ianchung621/qetool.git
   ```

4. For normal plotting, qetool needs `numpy` and `matplotlib`. XSF conversion additionally needs ASE; install qetool with its ASE extra only when using `in2xsf` or `inout2xsf`.

   ```bash
   pip install 'qetool[ase] @ git+https://github.com/ianchung621/qetool.git'
   ```

## General Workflow

- Run plotting commands from the folder containing the relevant output files whenever possible.
- Use explicit flags when multiple matching files are present.
- Default behavior saves PNG files, which is usually best on HPC. Use `--display` only when an interactive display is available.
- Keep generated plots in the same calculation subfolder unless the user asks for a separate report/output folder.
- If a command cannot infer a prefix because there are zero or multiple seed files, pass `--prefix`.
- When asked for a quick plot, make the plot and report the output file path; do not over-explain unless something fails.

## Command Selection

Use these commands:

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

## Expected Folder Layouts

Electronic:

```text
material/
  01-SCF/
    scf.in
    scf.out
  02-DOS/
    nscf.in
    nscf.out
    Material.pdos_tot
    Material.pdos_atm#1(Material)_wfc#1(s)
  03-BAND/
    band.in
    bands.in
    Material_bands.dat.gnu
```

Wannier/postw90 optics:

```text
material/
  7-POSTW/
    Material.win
    Material-kubo_S_xx.dat
    Material-kubo_A_xy.dat
    Material-jdos.dat
```

Phonons:

```text
material/
  3-PHONON/
    matdyn.in
    high_sym.txt
    Material.freq
    Material.freq.gp
    Material.phonon.dos
    lambda
    a2F.dos1
```

Bulk modulus:

```text
material/
  01-SCF/
    scf.in
    a0.98_scf.out
    a0.99_scf.out
    a1_scf.out
    a1.01_scf.out
    a1.02_scf.out
```

## DOS

Run in the DOS folder:

```bash
qe plot_dos --gap
```

Use explicit inputs when needed:

```bash
qe plot_dos \
  --pdos-tot Material.pdos_tot \
  --nscf-in nscf.in \
  --nscf-out nscf.out \
  --group elem,orb \
  --save-png Material_dos.png
```

Important flags:

- `--group orb`, `--group elem,orb`, or `--group elem,site,orb` groups QE `*.pdos_atm*` files.
- `--xlim -8 7` sets the energy window relative to Fermi energy.
- Output defaults to `<prefix>_dos.png`.

## Band Structure

Run in the band folder:

```bash
qe plot_band --gap
```

For spin-polarized data:

```bash
qe plot_band \
  --band-in band.in \
  --bands-in bands_up.in,bands_dn.in \
  --nscf-out ../02-DOS/nscf.out
```

Expected inputs:

- `band.in` with `K_POINTS crystal_b` labels in comments, such as `! G`, `! X`, `! M`.
- `bands.in` or `bands_up.in,bands_dn.in`, each with `filband = '...'`.
- `<filband>.gnu` files from `bands.x`.

If k-point labels fail because QE reduced the path, advise rerunning with `nosym = .true.`, `noinv = .true.` in the band input and `lsym = .false.` in `bands.in`.

Output defaults to `<prefix>_band.png`.

## Bulk Modulus

Prepare scaled inputs:

```bash
qe bulk_modulus --prepare
```

Analyze completed outputs:

```bash
qe bulk_modulus
```

Include magnetization:

```bash
qe bulk_modulus --magvol
```

Expected inputs:

- Prepare mode needs `scf.in` with `CELL_PARAMETERS`.
- Analysis mode needs at least three `a*_scf.out` files with `! total energy = ... Ry`.

Outputs:

- `bulk_EV.png`
- `bulk_EV_data.csv`
- With `--magvol`: `bulk_MV.png` and `bulk_MV_marked.png`

## Optics and Kerr

Run in the `postw90` output folder.

Optical conductivity:

```bash
qe plot_opt S_xx --jdos
qe plot_opt A_xy --prefix Material --soc
```

Dielectric function:

```bash
qe plot_die --component S_xx --eps-inf 1.0
```

Kerr rotation and ellipticity:

```bash
qe plot_kerr --prefix Material
```

Expected inputs:

- Optical conductivity: `<prefix>-kubo_<component>.dat`, with columns energy, real, imaginary.
- JDOS overlay: `<prefix>-jdos.dat`.
- Kerr: `<prefix>-kubo_S_xx.dat` and `<prefix>-kubo_A_xy.dat` on the same energy grid.
- A single `*.win` file lets qetool infer `prefix`; otherwise pass `--prefix`.

Outputs default to:

- `<prefix>_opt_cond_<component>.png`
- `<prefix>_dielectric_<component>.png`
- `<prefix>_kerr.png`

Use `--soc` for SOC or magnetic calculations so the tool does not apply a spin-degeneracy factor.

## Phonons and a2F

Run in the phonon folder:

```bash
qe plot_phonon_band
qe plot_phonon_dos
qe plot_a2f
```

Useful explicit flags:

```bash
qe plot_phonon_band --prefix Material --freq-gp Material.freq.gp --unit meV
qe plot_phonon_dos --prefix Material --phonon-dos Material.phonon.dos --energy-unit meV
qe plot_a2f --prefix Material --energy-unit meV
```

Expected inputs:

- Band: `<prefix>.freq.gp`, usually with `matdyn.in` and `high_sym.txt`.
- DOS: `<prefix>.phonon.dos`.
- a2F: `lambda` plus `a2F.dos1`, `a2F.dos2`, etc.
- A single `*.freq` file lets qetool infer `prefix`; otherwise pass `--prefix`.

Outputs default to:

- `<prefix>_phonon_band.png`
- `<prefix>_phonon_dos.png`
- `<prefix>_a2f.png`

## XSF Conversion

Use only when ASE is installed.

```bash
qe in2xsf scf.in
qe inout2xsf --scf_in scf.in --scf_out scf.out --axis 0 0 1
```

Expected inputs:

- `in2xsf`: QE input readable by ASE's `espresso-in` parser.
- `inout2xsf`: QE input plus output containing `Magnetic moment per site` and `magn=` values.

Output defaults to `<prefix>.xsf`.

## Failure Handling

- If inference fails, list matching files with `find` or `rg --files` and rerun with explicit flags.
- If no Fermi level is found, use `--nscf-out` or accept that band-gap/Fermi annotations may be skipped.
- If plotting fails on HPC due to display issues, rerun without `--display`.
- If `qe` is unavailable, tell the user what environment was checked and the minimal install command needed.
