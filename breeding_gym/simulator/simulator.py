from pathlib import Path
import numpy as np
import pandas as pd
from breeding_gym.simulator.gebv_model import GEBVModel
from breeding_gym.utils.paths import DATA_PATH
import jax
import jax.numpy as jnp


@jax.jit
def _cross(parent, crossover_mask):
    crossover_mask = crossover_mask.astype(jnp.int8)
    progenies = jnp.take_along_axis(
        parent,
        crossover_mask[:, None],
        axis=-1
    )

    return progenies.squeeze()


class BreedingSimulator:

    def __init__(
        self,
        genetic_map: Path = DATA_PATH.joinpath("genetic_map.txt"),
        trait_names: list[str] = ["Yield"],
        h2: list[int] | None = None
    ):
        if h2 is None:
            h2 = len(trait_names) * [1]
        assert len(h2) == len(trait_names)
        self.h2 = np.array(h2)
        self.trait_names = trait_names

        types = {'Chr': 'int32', 'RecombRate': 'float32', "Effect": 'float32'}
        genetic_map_df = pd.read_table(genetic_map, sep="\t", dtype=types)

        mrk_effects = genetic_map_df["Effect"]
        self.GEBV_model = GEBVModel(
            marker_effects=mrk_effects.to_numpy()[:, None]
        )

        self.n_markers = len(genetic_map_df)
        self.recombination_vec = genetic_map_df["RecombRate"].to_numpy()

        # change semantic to "recombine now" instead of "recombine after"
        self.recombination_vec[1:] = self.recombination_vec[:-1]

        chr_map = genetic_map_df['Chr']
        first_mrk_map = np.zeros(len(chr_map), dtype='bool')
        first_mrk_map[1:] = chr_map[1:].values != chr_map[:-1].values
        first_mrk_map[0] = True
        self.recombination_vec[first_mrk_map] = 0.5  # first equally likely

    def cross(self, parents: np.ndarray):
        cross_progeny = jax.vmap(self._cross_progeny, 0, 0)
        res = cross_progeny(parents)
        return res

    def _cross_progeny(self, parents: np.ndarray):
        cross_parent = jax.vmap(self._cross_parent, 0, 1)
        return cross_parent(parents)

    def _cross_parent(self, parent: np.ndarray):
        crossover_mask = self._get_crossover_mask()
        return _cross(parent, crossover_mask)

    def _get_crossover_mask(self):
        samples = np.random.rand(self.n_markers)
        recombination_sites = samples < self.recombination_vec
        return np.logical_xor.accumulate(recombination_sites)

    def GEBV(self, population: np.ndarray) -> pd.DataFrame:
        GEBV = self.GEBV_model(population)
        return pd.DataFrame(GEBV, columns=self.trait_names)

    def phenotype(self, population: np.ndarray):
        env_effect = (1 - self.h2) * self.var_gebv * \
            np.random.randn(len(self.h2))
        return self.h2 * self.GEBV(population) + env_effect

    def corrcoef(self, population: np.ndarray):
        monoploid_enc = population.reshape(population.shape[0], -1)
        mean_pop = np.mean(monoploid_enc, axis=0, dtype=np.float32)
        pop_with_centroid = np.vstack([mean_pop, monoploid_enc])
        corrcoef = np.corrcoef(pop_with_centroid, dtype=np.float32)
        return corrcoef[0, 1:]

    @property
    def max_gebv(self):
        return self.GEBV_model.max

    @property
    def min_gebv(self):
        return self.GEBV_model.min

    @property
    def mean_gebv(self):
        return self.GEBV_model.mean

    @property
    def var_gebv(self):
        return self.GEBV_model.var
