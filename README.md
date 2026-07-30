# BW-KEM Evaluation

This repository contains the scripts used to evaluate the security and
decryption-failure rates of the BW-KEM parameter sets. It accompanies the
submission and provides the evaluation code needed to reproduce the
corresponding results reported in the paper.

The scripts evaluate:

- the security of the underlying Module-LWE instances using primal and dual
  lattice attacks;
- the communication costs of the BW-KEM parameter sets; and
- the decryption-failure rate using the noncentral chi-squared approximation
  described in the paper.

Both the recommended parameter sets and the alternative security parameter
sets are included.

## Repository Structure

```text
.
├── BWKEM.py                 # Main evaluation script and parameter sets
├── BWKEM_failure.py         # Decryption-failure-rate estimation
├── MLWE_security.py         # Module-LWE security estimation
├── model_BKZ.py             # BKZ and Core-SVP cost models
├── proba_util.py            # Probability-distribution utilities
├── output/                  # Precomputed discrete distributions
├── requirements.txt         # Python dependencies
├── README.md
└── LICENSE
```

## Requirements

The scripts were tested with the following environment:

- Python 3.8.10
- NumPy 1.24.4
- SciPy 1.10.1

Install the required Python packages using:

```bash
python3 -m pip install -r requirements.txt
```

The corresponding `requirements.txt` contains:

```text
numpy>=1.24
scipy>=1.10
```

A recent version of SciPy is recommended because the decryption-failure
estimator relies on `scipy.stats.ncx2.logsf`.

## Usage

Clone the repository and enter its root directory:

```bash
git clone https://github.com/BW-KEM/evaluation.git
cd evaluation
```

Run the complete evaluation with:

```bash
python3 BWKEM.py
```

The script evaluates the following parameter sets:

- BW-KEM-512
- BW-KEM-768
- BW-KEM-1024
- BW-KEM-512-s
- BW-KEM-768-s
- BW-KEM-1024-s

For each parameter set, the output includes:

- public-key, ciphertext, and total communication costs;
- primal and dual Module-LWE security estimates;
- the block decryption-failure probability; and
- the overall DFR obtained using a union bound over all blocks.

## Precomputed Distributions

The `output/` directory contains precomputed distributions of

$$
S_i=\left\Vert(e_2+\epsilon_v)_i\right\Vert_2^2
$$

for the included parameter sets.

These files are automatically loaded by `BWKEM_failure.py` and substantially
reduce the running time of repeated evaluations.

The cached distributions are deterministic and are not required for
correctness. They can be safely deleted. When a required cache file is absent,
the script recomputes the distribution and stores the resulting `.npz` file in
the `output/` directory.

The cache filename records the parameters that determine the distribution:

```text
Dnorm_q_<q>_rq2_<rq2>_n_<n>_ke_ct_<ke_ct>.npz
```

## Reproducibility Notes

Run the scripts from the repository root so that the default `output/`
directory is resolved consistently.

If the precomputed distributions are present, they are loaded automatically.
To regenerate them, delete the corresponding `.npz` files from `output/` and
run:

```bash
python3 BWKEM.py
```

The generated cache files depend only on the parameter values encoded in their
filenames.

Minor differences in displayed floating-point values may occur across Python,
NumPy, or SciPy versions, but the reported security levels and DFR exponents
should remain consistent.

## Third-Party Acknowledgment

Parts of the lattice-security-estimation framework in `MLWE_security.py` and
`model_BKZ.py` are based on the methodology and scripts provided by the
PQ-Crystals security-estimates project:

```text
https://github.com/pq-crystals/security-estimates
```

The original authors and contributors retain attribution for the portions
derived from their work.

## Citation

The bibliographic information for the accompanying BW-KEM paper will be added
after publication.

When referring specifically to the evaluation software, please cite the
repository:

```text
https://github.com/BW-KEM/evaluation
```

## License

See the `LICENSE` file for the licensing terms applicable to this repository.
Third-party-derived portions remain subject to any applicable terms of their
original sources.
