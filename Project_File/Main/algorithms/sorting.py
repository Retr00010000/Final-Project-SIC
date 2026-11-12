import time

class SortMetrics:
    def __init__(self, algorithm=""):
        self.algorithm = algorithm
        self.comparisons = 0
        self.swaps = 0
        self.calls = 0
        self.elapsed_ms = 0.0

    def as_dict(self):
        return {"algorithm": self.algorithm, "comparisons": self.comparisons, "swaps/moves": self.swaps,
                "recursive calls": self.calls, "time (ms)": round(self.elapsed_ms, 3)}

def _identity(x):
    return x

def merge_sort(items, key=None, reverse=False):
    """Divide-and-conquer. O(n log n) in best/average/worst case, O(n) extra space, STABLE."""
    key = key or _identity
    metrics = SortMetrics("Merge Sort")
    start = time.perf_counter()

    def _sort(arr):
        metrics.calls += 1
        if len(arr) <= 1:
            return arr
        mid = len(arr) // 2
        left, right = _sort(arr[:mid]), _sort(arr[mid:])
        merged, i, j = [], 0, 0
        while i < len(left) and j < len(right):
            metrics.comparisons += 1
            a, b = key(left[i]), key(right[j])
            take_left = (a >= b) if reverse else (a <= b)    
            if take_left:
                merged.append(left[i]); i += 1
            else:
                merged.append(right[j]); j += 1
            metrics.swaps += 1
        for rest, idx in ((left, i), (right, j)):
            for item in rest[idx:]:
                merged.append(item)
                metrics.swaps += 1
        return merged

    result = _sort(list(items))
    metrics.elapsed_ms = (time.perf_counter() - start) * 1000
    return result, metrics

def quick_sort(items, key=None, reverse=False):

    key = key or _identity
    metrics = SortMetrics("Quick Sort")
    start = time.perf_counter()
    data = [(key(x), x) for x in items]           

    def before(a, b):
        return a > b if reverse else a < b

    def swap(i, j):
        if i != j:
            data[i], data[j] = data[j], data[i]
            metrics.swaps += 1

    def _sort(lo, hi):
        while lo < hi:
            metrics.calls += 1
            pivot = data[(lo + hi) // 2][0]
            lt, i, gt = lo, lo, hi
            while i <= gt:
                k = data[i][0]
                metrics.comparisons += 1
                if before(k, pivot):
                    swap(lt, i); lt += 1; i += 1
                else:
                    metrics.comparisons += 1
                    if before(pivot, k):
                        swap(i, gt); gt -= 1
                    else:
                        i += 1
            if lt - lo < hi - gt:
                _sort(lo, lt - 1); lo = gt + 1
            else:
                _sort(gt + 1, hi); hi = lt - 1

    _sort(0, len(data) - 1)
    metrics.elapsed_ms = (time.perf_counter() - start) * 1000
    return [x for _, x in data], metrics
