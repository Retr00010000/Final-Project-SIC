
class HashTable:
    def __init__(self, capacity=64, max_load=0.75):
        self.capacity = capacity
        self.max_load = max_load
        self.buckets = [[] for _ in range(capacity)]
        self.size = 0
        self.last_probes = 0

    def _hash(self, key):
        h = 0
        for ch in str(key):
            h = (h * 31 + ord(ch)) % self.capacity
        return h

    def insert(self, key, value):
        bucket = self.buckets[self._hash(key)]
        for i, (k, _) in enumerate(bucket):
            if k == key:
                bucket[i] = (key, value)       # update existing key
                return
        bucket.append((key, value))
        self.size += 1
        if self.load_factor() > self.max_load:
            self._resize()

    def get(self, key, default=None):
        self.last_probes = 0
        for k, v in self.buckets[self._hash(key)]:
            self.last_probes += 1
            if k == key:
                return v
        return default

    def delete(self, key):
        bucket = self.buckets[self._hash(key)]
        for i, (k, _) in enumerate(bucket):
            if k == key:
                del bucket[i]
                self.size -= 1
                return True
        return False

    def load_factor(self):
        return self.size / self.capacity

    def _resize(self):
        old = list(self.items())
        self.capacity *= 2
        self.buckets = [[] for _ in range(self.capacity)]
        self.size = 0
        for k, v in old:
            self.insert(k, v)

    def items(self):
        for bucket in self.buckets:
            for pair in bucket:
                yield pair

    def keys(self):
        return [k for k, _ in self.items()]

    # ---- (dashboard) ----
    def bucket_lengths(self):
        return [len(b) for b in self.buckets]

    def collisions(self):
        """Entries that share a bucket with an earlier entry."""
        return sum(max(0, len(b) - 1) for b in self.buckets)

    def longest_chain(self):
        return max(self.bucket_lengths(), default=0)

    def __len__(self):
        return self.size

    def __contains__(self, key):
        marker = object()
        return self.get(key, marker) is not marker
