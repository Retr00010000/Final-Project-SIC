import random

def _identity(x):
    return x

def sequential_find(items, target, key=None):
    key = key or _identity
    steps = 0
    for i, item in enumerate(items):
        steps += 1
        if key(item) == target:
            return i, steps
    return -1, steps

def sequential_search(items, predicate):
    matches, steps = [], 0
    for item in items:
        steps += 1
        if predicate(item):
            matches.append(item)
    return matches, steps

def lower_bound(sorted_items, target, key=None):
    
    key = key or _identity
    lo, hi, steps = 0, len(sorted_items), 0
    while lo < hi:
        mid = (lo + hi) // 2
        steps += 1
        if key(sorted_items[mid]) < target:
            lo = mid + 1
        else:
            hi = mid
    return lo, steps

def binary_search(sorted_items, target, key=None):
    
    key = key or _identity
    idx, steps = lower_bound(sorted_items, target, key)
    if idx < len(sorted_items) and key(sorted_items[idx]) == target:
        return idx, steps
    return -1, steps

def range_search(sorted_items, start, end, key=None):
   
    lo, s1 = lower_bound(sorted_items, start, key)
    hi, s2 = lower_bound(sorted_items, end, key)
    return sorted_items[lo:hi], s1 + s2

def benchmark_lookup(sorted_items, key, samples=200, seed=0):
    #Average steps of sequential vs binary exact lookup over random existing keys.
    if not sorted_items:
        return {"samples": 0, "sequential_avg": 0.0, "binary_avg": 0.0}
    rng = random.Random(seed)
    targets = [key(rng.choice(sorted_items)) for _ in range(samples)]
    seq = sum(sequential_find(sorted_items, t, key)[1] for t in targets)
    binary = sum(binary_search(sorted_items, t, key)[1] for t in targets)
    return {"samples": samples, "sequential_avg": seq / samples, "binary_avg": binary / samples}
