import gym
import numpy as np
from breeding_gym.utils.paths import DATA_PATH
import pytest


def test_reset_population():
    env = gym.make("BreedingGym",
                   initial_population=DATA_PATH.joinpath("small_geno.txt"),
                   genetic_map=DATA_PATH.joinpath("small_genetic_map.txt"),
                   )

    pop, _ = env.reset()
    init_pop = np.copy(pop)

    env.step(np.asarray(env.action_space.sample()) % len(pop))
    pop, _ = env.reset()
    assert np.all(init_pop == pop)


@pytest.mark.parametrize("n", [1, 5, 10])
def test_num_progenies(n):
    env = gym.make("BreedingGym",
                   initial_population=DATA_PATH.joinpath("small_geno.txt"),
                   genetic_map=DATA_PATH.joinpath("small_genetic_map.txt"),
                   )
    pop, _ = env.reset()

    action = np.random.randint(len(pop), size=(n, 2))
    env.step(action)

    assert len(env.population) == n


def test_caching():
    env = gym.make("BreedingGym",
                   initial_population=DATA_PATH.joinpath("small_geno.txt"),
                   genetic_map=DATA_PATH.joinpath("small_genetic_map.txt"),
                   )
    env.reset()

    GEBV = env.GEBV
    GEBV_copy = np.copy(GEBV)
    GEBV2 = env.GEBV
    assert id(GEBV) == id(GEBV2)
    assert np.all(GEBV_copy == GEBV2)

    corrcoef = env.corrcoef
    corrcoef_copy = np.copy(corrcoef)
    corrcoef2 = env.corrcoef
    assert id(corrcoef) == id(corrcoef2)
    assert np.all(corrcoef_copy == corrcoef2)

    action = np.array([[1, 3], [4, 2]])
    env.step(action)

    GEBV3 = env.GEBV
    corrcoef3 = env.corrcoef
    assert id(corrcoef) != id(corrcoef3)
    assert id(GEBV) != id(GEBV3)


def test_simplified_env():
    env = gym.make("SimplifiedBreedingGym",
                   individual_per_gen=200,
                   initial_population=DATA_PATH.joinpath("small_geno.txt"),
                   genetic_map=DATA_PATH.joinpath("small_genetic_map.txt"),
                   )
    env.reset()
    env.step({"n_bests": 10, "n_crosses": 20})
    env.step({"n_bests": 21, "n_crosses": 200})
    env.step({"n_bests": 2, "n_crosses": 1})

    with pytest.raises(Exception):
        env.step({"n_bests": 2, "n_crosses": 10})

    with pytest.raises(Exception):
        env.step({"n_bests": 1, "n_crosses": 1})

    with pytest.raises(Exception):
        env.step({"n_bests": 500, "n_crosses": 10})


def test_kbest_env():
    env = gym.make("KBestBreedingGym",
                   individual_per_gen=200,
                   initial_population=DATA_PATH.joinpath("small_geno.txt"),
                   genetic_map=DATA_PATH.joinpath("small_genetic_map.txt"),
                   )
    env.reset()
    env.step(10)
    env.step(2)
    env.step(200)

    with pytest.raises(Exception):
        env.step(1)

    with pytest.raises(Exception):
        env.step(201)


def test_reward_shaping():
    env = gym.make("BreedingGym",
                   initial_population=DATA_PATH.joinpath("small_geno.txt"),
                   genetic_map=DATA_PATH.joinpath("small_genetic_map.txt"),
                   reward_shaping=False
                   )

    pop, _ = env.reset()

    for _ in range(9):
        action = np.asarray(env.action_space.sample()) % len(pop)
        pop, reward, _, truncated, _ = env.step(action)

        assert reward == 0
        assert not truncated

    action = np.asarray(env.action_space.sample()) % len(pop)
    _, reward, _, truncated, _ = env.step(action)

    assert reward != 0
    assert truncated
