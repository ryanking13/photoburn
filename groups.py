class Groups:

    def __init__(self, keys):
        self._rank = {str(key): 0 for key in keys}
        self._parent = {str(key): str(key) for key in keys}

    def find(self, x):
        if self._parent[x] == x:
            return x
        else:
            self._parent[x] = self.find(self._parent[x])
            return self._parent[x]

    def unite(self, x, y):
        x = self.find(x)
        y = self.find(y)

        if x == y:
            return
        else:
            if self._rank[x] < self._rank[y]:
                self._parent[x] = y
            else:
                self._parent[y] = x
                if self._rank[x] == self._rank[y]:
                    self._rank[x] += 1

    def same(self, x, y):
        return self.find(x) == self.find(y)

    def get(self):
        return self._parent
