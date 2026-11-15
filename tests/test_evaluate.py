import unittest

import numpy as np

from eval.evaluate import (group_hits, random_group_rates, random_label_ratio,
                           same_label_ratios, top_neighbors)

# 질문 4개: 0·1이 같은 묶음, 2·3이 같은 묶음
SIMILARITY = np.array([
    [1.0, 0.9, 0.2, 0.1],
    [0.9, 1.0, 0.3, 0.8],
    [0.2, 0.3, 1.0, 0.4],
    [0.1, 0.8, 0.4, 1.0],
])
GROUPS = ["G01", "G01", "G02", "G02"]


class EvaluateTests(unittest.TestCase):
    def test_neighbors_skip_self(self):
        neighbors = top_neighbors(SIMILARITY, 2)
        self.assertEqual(neighbors, [[1, 2], [0, 3], [3, 1], [1, 2]])

    def test_neighbors_tie_keeps_order(self):
        neighbors = top_neighbors(np.ones((3, 3)), 2)
        self.assertEqual(neighbors, [[1, 2], [0, 2], [0, 1]])

    def test_group_hits(self):
        neighbors = top_neighbors(SIMILARITY, 2)
        # 1등이 같은 묶음: 0, 1, 2 / 2개 안에 있음: 0, 1, 2, 3
        self.assertEqual(group_hits(neighbors, GROUPS), (3, 4))

    def test_same_label_ratios(self):
        neighbors = top_neighbors(SIMILARITY, 2)
        self.assertEqual(same_label_ratios(neighbors, GROUPS), [0.5, 0.5, 0.5, 0.5])

    def test_random_baselines(self):
        top1, topk = random_group_rates(GROUPS, 2)
        self.assertAlmostEqual(top1, 1 / 3)
        self.assertAlmostEqual(topk, 2 / 3)
        self.assertAlmostEqual(random_label_ratio(GROUPS), 1 / 3)


if __name__ == "__main__":
    unittest.main()
