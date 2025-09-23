import os
import sys

sys.path.insert(0,
                os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import src.analyzer
import numpy as np
import unittest


class TestAnalysis(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.analyzer = src.analyzer.Analyzer()
        self.analyzer.testing_init()

        # maximum number of images allowed to fail for each function
        self.max_value = 10

    def _failed_count(self):
        def failed_count_helper(failed, directory):
            files = os.listdir(self.analyzer.dir + directory)
            count = [0 for _ in range(len(self.analyzer.functions))]
            for file in files:
                p = os.path.join(self.analyzer.dir + directory, file)
                if os.path.isfile(p):
                    for i in range(len(self.analyzer.functions)):
                        if self.analyzer.functions[i](p)[0] == failed:
                            count[i] += 1
            return count

        agitated_count = failed_count_helper(False, '/agitated')
        base_count = failed_count_helper(True, '/base')
        print(f"Failed count: {agitated_count}")
        print(f"Failed count: {base_count}")
        return [agitated_count, base_count]

    def tests(self):
        self.assertTrue(np.all(np.array(
            self._failed_count(), dtype=np.float32).flatten() < self.max_value))


if __name__ == '__main__':
    print(__doc__)
    unittest.main()
