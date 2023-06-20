flat_map = lambda f, xs: (y for ys in xs for y in f(ys))
