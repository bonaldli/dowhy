import copy

import numpy as np
import logging

from dowhy.causal_refuter import CausalRefutation
from dowhy.causal_refuter import CausalRefuter
from dowhy.causal_estimator import CausalEstimator

class RandomCommonCause(CausalRefuter):
    """Refute an estimate by introducing a randomly generated confounder
    (that may have been unobserved).

    :param num_simulations: The number of simulations to be run, which is ``CausalRefuter.DEFAULT_NUM_SIMULATIONS`` by default
    :type num_simulations: int, optional

    :param random_state: The seed value to be added if we wish to repeat the same random behavior. If we with to repeat the same behavior we push the same seed in the psuedo-random generator
    :type random_state: int, RandomState, optional
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._num_simulations = kwargs.pop("num_simulations", CausalRefuter.DEFAULT_NUM_SIMULATIONS )
        self._random_state = kwargs.pop("random_state",None)

        self.logger = logging.getLogger(__name__)

    def refute_estimate(self):
        num_rows = self._data.shape[0]
        sample_estimates = np.zeros(self._num_simulations)
        self.logger.info("Refutation over {} simulated datasets, each with a random common cause added"
                         .format(self._num_simulations))

        new_backdoor_variables = self._target_estimand.get_backdoor_variables() + ['w_random']
        identified_estimand = copy.deepcopy(self._target_estimand)
        # Adding a new backdoor variable to the identified estimand
        identified_estimand.set_backdoor_variables(new_backdoor_variables)
        for index in range(self._num_simulations):
            if self._random_state is None:
                new_data = self._data.assign(w_random=np.random.randn(num_rows))
            else:
                new_data = self._data.assign(w_random=self._random_state.normal(size=num_rows
                                             ))

            new_estimator = CausalEstimator.get_estimator_object(new_data, identified_estimand, self._estimate)
            new_effect = new_estimator.estimate_effect()

            sample_estimates[index] = new_effect.value

        refute = CausalRefutation(
            self._estimate.value,
            np.mean(sample_estimates),
            refutation_type="Refute: Add a random common cause"
        )

        # We want to see if the estimate falls in the same distribution as the one generated by the refuter
        # Ideally that should be the case as choosing a subset should not have a significant effect on the ability
        # of the treatment to affect the outcome
        refute.add_significance_test_results(
            self.test_significance(self._estimate, sample_estimates)
        )

        refute.add_refuter(self)
        return refute
