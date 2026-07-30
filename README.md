# Security and DFR Estimates for BW-KEM

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

This repository contains the scripts used to evaluate the security and DFR of the
recommended BW-KEM parameter sets.

---

## Repository Structure

```text
.
├── BWKEM.py                 # Main script
├── BWKEM_failure.py         # DFR estimation
├── MLWE_security.py         # MLWE security estimation
├── model_BKZ.py             # BKZ/Core-SVP cost model
├── proba_util.py            # Probability utilities
├── output/                  # Cached discrete distributions
└── LICENSE
```

---

## Requirements

The scripts were tested with

- Python 3.8.10
- NumPy 1.24.4
- SciPy 1.10.1

Install the required packages using

```bash
pip install -r requirements.txt
```

or

```bash
pip install numpy scipy
```

---

## Running the Evaluation

Run

```bash
python3 BWKEM.py
```

The script evaluates all recommended BW-KEM parameter sets and reports

- communication cost,
- estimated MLWE security,
- decryption failure rate.

---

## Cached Discrete Distributions

The DFR estimator computes the distribution

\[
S_i=\|(e_2+\epsilon_v)_i\|_2^2
\]

which depends only on the parameter set.

During the first execution, this distribution is computed and stored in
the `output/` directory. Subsequent executions automatically reuse the
cached data, significantly reducing the running time.

The cached files are deterministic and can be safely deleted. They will
be regenerated automatically when needed.

---

## Acknowledgements

We would like to express our gratitude to the authors of the [pq-crystals/security-estimates](https://github.com/pq-crystals/security-estimates) repository. Portions of our security estimation scripts are adapted from their codebase.
