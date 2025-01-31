import os
import timeit

import jax
import numpy as np
import pandas as pd
from chromax import Simulator
from chromax.index_functions import phenotype_index


def wheat_schema(
    simulator: Simulator,
    germplasm,
    factor=1,
):
    f1, _ = simulator.random_crosses(germplasm, 200 * factor)
    dh_lines = simulator.double_haploid(f1, n_offspring=100)

    dh_lines = dh_lines.reshape(200 * factor, 100, *dh_lines.shape[1:])
    vmap_select, _ = jax.vmap(simulator.select, (0, None, None))
    headrows = vmap_select(dh_lines, 5, visual_selection(simulator, seed=7))
    headrows = headrows.reshape(1000 * factor, -1, 2)
    # hdrw_next_year, _ = simulator.select(
    #     dh_lines,
    #     k=20,
    #     f_index=visual_selection(simulator, seed=7)
    # )

    envs = simulator.create_environments(num_environments=16)
    pyt, _ = simulator.select(
        headrows, k=100 * factor, f_index=phenotype_index(simulator, envs[0])
    )
    # pyt_next_year, _ = simulator.select(
    #     headrows,
    #     k=20,
    #     f_index=phenotype_index(simulator, envs[0])
    # )
    ayt, _ = simulator.select(
        pyt, k=10 * factor, f_index=phenotype_index(simulator, envs[:4])
    )

    released_variety, _ = simulator.select(
        ayt, k=1, f_index=phenotype_index(simulator, envs)
    )

    # next_year_germplasm = np.concatenate(
    #     (pyt_next_year, ayt, hdrw_next_year),
    #     axis=0
    # )
    return released_variety


def visual_selection(simulator, noise_factor=1, seed=None):
    generator = np.random.default_rng(seed)

    def visual_selection_f(population):
        phenotype = simulator.phenotype(population)[..., 0]
        noise_var = simulator.GEBV_model.var * noise_factor
        noise = generator.normal(scale=noise_var, size=phenotype.shape)
        return phenotype + noise

    return visual_selection_f


if __name__ == "__main__":
    repeats = 100
    n_chr = 21
    chr_len = 100
    factor = 1
    times = np.empty(repeats)
    print(os.system("lscpu"))
    print(os.system("nvidia-smi -L"))

    genetic_map = pd.DataFrame(
        {
            "CHR.PHYS": np.arange(n_chr * chr_len, dtype=np.int32) // chr_len,
            "Yield": np.random.standard_normal(n_chr * chr_len).astype(np.float32),
            "RecombRate": np.full(n_chr * chr_len, 1.5 / 1000),
        }
    )
    simulator = Simulator(genetic_map=genetic_map)

    for i in range(repeats):
        germplasm = np.random.choice(
            a=[False, True], size=(50 * factor, n_chr * chr_len, 2), p=[0.5, 0.5]
        )

        t = timeit.timeit(
            lambda: wheat_schema(simulator, germplasm, factor)[0].block_until_ready(),
            number=1,
        )
        times[i] = t
        del germplasm

    print(times)
    print("Mean", np.mean(times[1:]))
    print("Std", np.std(times[1:]))
