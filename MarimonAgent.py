import numpy as np
from itertools import product
from AbstractClasses import Agent


class MarimonAgent(Agent):

    name = "Marimon"

    def __init__(self, **kwargs):

        super().__init__(**kwargs)

        self.exchange_classifier_system = ExchangeClassifierSystem(
            b11=self.agent_parameters["b11"],
            b12=self.agent_parameters["b12"],
            initial_strength=self.agent_parameters["initial_strength"])
        self.consumption_classifier_system = ConsumptionClassifierSystem(
            b21=self.agent_parameters["b21"],
            b22=self.agent_parameters["b22"],
            initial_strength=self.agent_parameters["initial_strength"])

        self.previous_object_in_hand = self.P

        self.utility_derived_from_consumption = self.agent_parameters["u"]

        self.best_exchange_classifier = None
        self.best_consumption_classifier = None

        self.prepare_classifiers()

    def prepare_classifiers(self):

        self.exchange_classifier_system.prepare_classifiers()
        self.consumption_classifier_system.prepare_classifiers()

    def are_you_satisfied(self, proposed_object, type_of_other_agent, proportions):

        # Choose the right classifier

        # Equation 5
        m_index = self.exchange_classifier_system.get_potential_bidders(self.in_hand, proposed_object)

        # assert len(m_index) == 18

        # Equation 6
        self.best_exchange_classifier = self.exchange_classifier_system.get_best_classifier(m_index)

        # Look at the decision

        # Equation 1
        exchange_decision = bool(self.best_exchange_classifier.decision)

        return exchange_decision

    def consume(self):

        # Choose the right classifier

        # Is there a winning exchange classifier?
        # is_winning_exchange_classifier = 1
        is_winning_exchange_classifier = \
            self.best_exchange_classifier.decision == 0 \
            or self.exchange is True

        # Update strength of previous selected classifier
        if self.best_consumption_classifier:

            if is_winning_exchange_classifier:
                exchange_classifier_bid = self.best_exchange_classifier.get_bid()
            else:
                exchange_classifier_bid = 0

            self.best_consumption_classifier.update_strength(
                utility=self.utility_derived_from_consumption*self.consumption
                    - self.storing_costs[self.previous_object_in_hand],
                exchange_classifier_bid=exchange_classifier_bid
            )

        # ------------- #

        # Re-initialize
        self.consumption = 0

        # Equation 7
        m_index = self.consumption_classifier_system.get_potential_bidders(self.in_hand)

        # Equation 8
        self.best_consumption_classifier = self.consumption_classifier_system.get_best_classifier(m_index)
        self.best_consumption_classifier.update_theta_counter()

        # Update
        if is_winning_exchange_classifier:
            self.best_exchange_classifier.update_theta_counter()
            self.best_exchange_classifier.update_strength(
                consumption_classifier_bid=self.best_consumption_classifier.get_bid())

        # If he decides to consume...
        # Equation 3 & 4
        if self.best_consumption_classifier.decision == 1:

            # And the agent has his consumption good
            if self.in_hand == self.C:
                self.consumption = 1

            # If he decided to consume, he produce a new unity of his production good
            self.in_hand = self.P

        # Keep a trace of the previous object in hand
        self.previous_object_in_hand = self.in_hand

# --------------------------------------------------------------------------------------------------- #
# -------------------------------- CLASSIFIER SYSTEM ------------------------------------------------ #
# --------------------------------------------------------------------------------------------------- #


class ClassifierSystem(object):

    def __init__(self):

        self.collection_of_classifiers = list()

        # Encoding of goods
        self.encoding_of_goods = np.array(
            [
                [1, 0, 0],  # Good 0
                [0, 1, 0],  # Good 1
                [0, 0, 1],  # Good 2
                [0, -1, -1],  # Not good 0
                [-1, 0, -1],  # Not good 1
                [-1, -1, 0]   # Not good 2
            ], dtype=int
        )

    def get_best_classifier(self, m_index):

        s = np.asarray([self.collection_of_classifiers[i].strength for i in m_index])

        # assert len(s) in [18, 6]

        best_m_idx = np.random.choice(np.where(s == max(s))[0])

        best_classifier_idx = m_index[best_m_idx]

        return self.collection_of_classifiers[best_classifier_idx]


class ExchangeClassifierSystem(ClassifierSystem):

    def __init__(self, b11, b12, initial_strength):

        super().__init__()

        self.b11 = b11
        self.b12 = b12
        self.initial_strength = initial_strength

    def prepare_classifiers(self):

        for i, j in product(self.encoding_of_goods, repeat=2):

            for k in [0, 1]:

                self.collection_of_classifiers.append(
                    ExchangeClassifier(
                        own_storage=i,
                        partner_storage=j,
                        decision=k,
                        strength=self.initial_strength,
                        b11=self.b11,
                        b12=self.b12
                    )
                )

    def get_potential_bidders(self, own_storage, partner_storage):

        # List of indexes of classifiers that match the current situation
        match_index = []
        for i, c in enumerate(self.collection_of_classifiers):

            if c.is_matching(own_storage, partner_storage):
                match_index.append(i)

        return match_index


class ConsumptionClassifierSystem(ClassifierSystem):

    def __init__(self, b21, b22, initial_strength):

        super().__init__()

        self.b21 = b21
        self.b22 = b22
        self.initial_strength = initial_strength

    def prepare_classifiers(self):

        for i in self.encoding_of_goods:

            for j in [0, 1]:

                self.collection_of_classifiers.append(
                    ConsumptionClassifier(
                        own_storage=i,
                        decision=j,
                        b21=self.b21,
                        b22=self.b22,
                        strength=self.initial_strength
                    )
                )

    def get_potential_bidders(self, own_storage):

        match_index = []
        for i, c in enumerate(self.collection_of_classifiers):

            if c.is_matching(own_storage):

                match_index.append(i)

        return match_index


# --------------------------------------------------------------------------------------------------- #
# -------------------------------- CLASSIFIER ------------------------------------------------------- #
# --------------------------------------------------------------------------------------------------- #

class Classifier(object):

    def __init__(self, strength, decision):

        self.strength = strength
        self.decision = decision

        # Equations 9 and 10
        self.theta_counter = 1

    def update_theta_counter(self):

        self.theta_counter += 1


class ExchangeClassifier(Classifier):

    def __init__(self, own_storage, partner_storage, decision, strength, b11, b12):

        super().__init__(strength=strength, decision=decision)

        self.own_storage = np.asarray(own_storage)
        self.partner_storage = np.asarray(partner_storage)

        self.sigma = 1 / (1 + sum(self.own_storage[:] == -1) + sum(self.partner_storage[:] == -1))

        # Equation 11a
        self.b1 = b11 + b12 * self.sigma

    def get_bid(self):

        # Def of a bid p 138
        return self.b1 * self.strength

    def update_strength(self, consumption_classifier_bid):

        self.strength -= (1 / self.theta_counter) * (
            self.get_bid() + self.strength
            - consumption_classifier_bid
        )

    def is_matching(self, own_storage, partner_storage):

        # Args are integers (0, 1 or 2)
        # self.own_storage is an array ([0, 0, 1] or [-1, -1, 0] and so on)
        cond_own_storage = self.own_storage[own_storage] != 0
        cond_partner_storage = self.partner_storage[partner_storage] != 0
        return cond_own_storage and cond_partner_storage


class ConsumptionClassifier(Classifier):

    def __init__(self, own_storage, strength, b21, b22, decision):

        super().__init__(strength=strength, decision=decision)

        # Object in hand at the end of the turn
        self.own_storage = np.asarray(own_storage)

        sigma = 1 / (1 + sum(self.own_storage[:] == -1))

        # Equation 11b
        self.b2 = b21 + b22 * sigma

    def get_bid(self):

        return self.b2 * self.strength

    def update_strength(self, exchange_classifier_bid, utility):

        # Equation 12
        self.strength -= (1 / (self.theta_counter - 1)) * (
            self.get_bid() + self.strength
            - exchange_classifier_bid - utility
        )

    def is_matching(self, own_storage):

        return self.own_storage[own_storage] != 0


def main():

    exh = ExchangeClassifierSystem(b11=0.35, b12=0.35, initial_strength=0)
    exh.prepare_classifiers()
    for i in exh.collection_of_classifiers:

        print(i.own_storage, i.partner_storage, i.decision, i.sigma)




if __name__ == "__main__":

    main()


