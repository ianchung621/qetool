module avail
module load tools/miniconda3

which python
python --version

conda create -n cmp
conda activate cmp
conda install pip
pip install numpy matplotlib ase

include this to .bashrc to avoid typing in every login:
``
module load tools/miniconda3
conda activate cmp
``