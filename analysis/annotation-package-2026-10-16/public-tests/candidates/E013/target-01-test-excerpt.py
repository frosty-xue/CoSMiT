def testBasic(self):
  self._testAll(np.arange(-10, 10).reshape(2, 10))
  self._testAll(np.linspace(-10, 10, 17))
