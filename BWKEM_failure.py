"""Decryption-failure-rate estimation for BW-KEM.

The polynomial-product part of each error block is approximated by an
isotropic Gaussian distribution.  After conditioning on the discrete part
D_i = (e_2 + epsilon_v)_i, the block error probability is evaluated through
a noncentral chi-squared mixture.

The distribution of S_i = ||D_i||_2^2 depends only on
(q, rq2, n, ke_ct).  It is cached in ``output/`` and reused for parameter
sets with the same four values.
"""

from __future__ import annotations

import math
import os
from pathlib import Path
from typing import Dict, Optional, Tuple

import numpy as np
from scipy.special import logsumexp
from scipy.stats import ncx2

from proba_util import (
    build_centered_binomial_law,
    build_law_square,
    build_mod_switching_error_law,
    law_convolution,
    var_of_law,
)

_LOG_2 = math.log(2.0)
_DEFAULT_CHUNK_SIZE = 100_000


def _default_output_dir() -> Path:
    """Return the directory used for cached discrete distributions."""
    return Path(__file__).resolve().parent / "output"


def _cache_path(ps, output_dir: Path) -> Path:
    """Return the cache filename determined by (q, rq2, n, ke_ct)."""
    filename = (
        f"Dnorm_q_{int(ps.q)}_rq2_{int(ps.rq2)}_"
        f"n_{int(ps.n)}_ke_ct_{int(ps.ke_ct)}.npz"
    )
    return output_dir / filename


def _build_discrete_norm_distribution(ps) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Compute the law of S_i = ||D_i||_2^2.
    Returns
    -------
    support:
        Integer values in the support of S_i.
    probabilities:
        Corresponding probabilities.
    log_probabilities:
        Natural logarithms of the probabilities.
    """
    e2_law = build_centered_binomial_law(int(ps.ke_ct))
    epsilon_v_law = build_mod_switching_error_law(int(ps.q), int(ps.rq2))
    coordinate_law = law_convolution(e2_law, epsilon_v_law)
    coordinate_square_law = build_law_square(coordinate_law, int(ps.q))

    shifts = np.fromiter(sorted(coordinate_square_law), dtype=np.int64)
    weights = np.fromiter(
        (coordinate_square_law[int(s)] for s in shifts),
        dtype=np.longdouble,
    )
    weights /= weights.sum(dtype=np.longdouble)

    max_shift = int(shifts[-1])
    distribution = np.array([1.0], dtype=np.longdouble)

    for _ in range(int(ps.n)):
        updated = np.zeros(distribution.size + max_shift, dtype=np.longdouble)
        for shift, weight in zip(shifts, weights):
            shift_int = int(shift)
            updated[shift_int : shift_int + distribution.size] += weight * distribution
        distribution = updated

    distribution /= distribution.sum(dtype=np.longdouble)

    positive = distribution > 0
    support = np.flatnonzero(positive).astype(np.int64, copy=False)
    probabilities_ld = distribution[positive]
    probabilities = probabilities_ld.astype(np.float64)
    log_probabilities = np.log(probabilities_ld).astype(np.float64)

    return support, probabilities, log_probabilities


def _load_cached_distribution(
    cache_file: Path,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Load a cached squared-norm distribution."""
    with np.load(cache_file, allow_pickle=False) as data:
        support = np.asarray(data["support"], dtype=np.int64)
        probabilities = np.asarray(data["probabilities"], dtype=np.float64)
        log_probabilities = np.asarray(data["log_probabilities"], dtype=np.float64)

    return support, probabilities, log_probabilities


def get_discrete_norm_distribution(
    ps,
    output_dir: Optional[os.PathLike] = None,
    force_recompute: bool = False,
    verbose: bool = True,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, Path, bool]:
    """Load or compute the law of S_i = ||D_i||_2^2."""
    cache_dir = Path(output_dir) if output_dir is not None else _default_output_dir()
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = _cache_path(ps, cache_dir)

    if cache_file.exists() and not force_recompute:
        try:
            support, probabilities, log_probabilities = _load_cached_distribution(cache_file)
            if verbose:
                print(f"discrete norm distribution: loaded {cache_file}")
            return support, probabilities, log_probabilities, cache_file, True
        except (OSError, KeyError, ValueError):
            if verbose:
                print(f"discrete norm cache cannot be loaded; recomputing it")

    support, probabilities, log_probabilities = _build_discrete_norm_distribution(ps)

    temporary_file = cache_file.with_suffix(cache_file.suffix + ".tmp")
    with temporary_file.open("wb") as handle:
        np.savez_compressed(
            handle,
            q=np.int64(ps.q),
            rq2=np.int64(ps.rq2),
            n=np.int64(ps.n),
            ke_ct=np.int64(ps.ke_ct),
            support=support,
            probabilities=probabilities,
            log_probabilities=log_probabilities,
        )
    os.replace(temporary_file, cache_file)

    if verbose:
        print(f"discrete norm distribution: computed and cached at {cache_file}")
    return support, probabilities, log_probabilities, cache_file, False


def _gaussian_variance(ps) -> float:
    """Return sigma^2 for the Gaussian polynomial-product component."""
    epsilon_u_variance = var_of_law(build_mod_switching_error_law(ps.q, ps.rqc))
    secret_variance = var_of_law(build_centered_binomial_law(ps.ks))
    public_error_variance = var_of_law(build_centered_binomial_law(ps.ke))
    ciphertext_error_variance = var_of_law(build_centered_binomial_law(ps.ke_ct))

    sigma2 = (
        ps.N
        * ps.l
        * secret_variance
        * (public_error_variance + ciphertext_error_variance + epsilon_u_variance)
    )
    return float(sigma2)


def _decoding_radius(ps) -> float:
    """Return the block decoding radius used by the original estimator."""
    q_power_of_two = 2 ** math.ceil(math.log2(ps.q))
    radius = (
        ps.q * math.sqrt(2.0 * ps.n) / (2 ** (ps.tau + 2))
        - math.sqrt(ps.n / 4.0) * (ps.q / q_power_of_two + 1.0)
    )
    return float(radius)


def _mixture_log_probability(
    support: np.ndarray,
    log_probabilities: np.ndarray,
    sigma2: float,
    radius2: float,
    degrees_of_freedom: int,
    chunk_size: int = _DEFAULT_CHUNK_SIZE,
) -> float:
    """Evaluate the noncentral-chi-squared mixture in the log domain."""
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive.")

    threshold = radius2 / sigma2
    total_log_probability = -math.inf

    for start in range(0, support.size, chunk_size):
        stop = min(start + chunk_size, support.size)
        noncentrality = support[start:stop].astype(np.float64) / sigma2
        log_tails = ncx2.logsf(threshold, degrees_of_freedom, noncentrality)
        if np.any(np.isnan(log_tails)):
            raise RuntimeError("scipy.stats.ncx2.logsf returned NaN.")

        chunk_log_probability = float(
            logsumexp(log_probabilities[start:stop] + log_tails)
        )
        total_log_probability = float(
            np.logaddexp(total_log_probability, chunk_log_probability)
        )

    return total_log_probability


def ErrorRate_BWKEM_NoncentralChiSquare(
    ps,
    output_dir: Optional[os.PathLike] = None,
    force_recompute: bool = False,
    verbose: bool = True,
) -> Dict[str, object]:
    """Estimate the BW-KEM DFR using a noncentral chi-squared mixture."""
    support, probabilities, log_probabilities, cache_file, cache_hit = (
        get_discrete_norm_distribution(
            ps,
            output_dir=output_dir,
            force_recompute=force_recompute,
            verbose=verbose,
        )
    )

    sigma2 = _gaussian_variance(ps)
    radius = _decoding_radius(ps)
    block_log_probability = _mixture_log_probability(
        support=support,
        log_probabilities=log_probabilities,
        sigma2=sigma2,
        radius2=radius * radius,
        degrees_of_freedom=int(ps.n),
    )

    number_of_blocks = int(ps.N // ps.n)
    dfr_union_log_probability = min(
        0.0,
        block_log_probability + math.log(number_of_blocks),
    )

    block_log2 = block_log_probability / _LOG_2
    dfr_union_log2 = dfr_union_log_probability / _LOG_2

    if verbose:
        print(
            "block failure probability "
            f"(noncentral chi-square approximation) ~= 2^{block_log2:.2f}"
        )
        print(
            f"estimated DFR (union bound over {number_of_blocks} blocks) "
            f"~= 2^{dfr_union_log2:.2f}"
        )

    return {
        "sigma2": sigma2,
        "radius": radius,
        "block_log_probability": block_log_probability,
        "block_log2_probability": block_log2,
        "dfr_union_log_probability": dfr_union_log_probability,
        "dfr_union_log2_probability": dfr_union_log2,
        "number_of_blocks": number_of_blocks,
        "discrete_support_size": int(support.size),
        "discrete_probability_mass": float(np.sum(probabilities, dtype=np.float64)),
        "cache_file": cache_file,
        "cache_hit": cache_hit,
    }


ErrorRate_BWKEM = ErrorRate_BWKEM_NoncentralChiSquare
