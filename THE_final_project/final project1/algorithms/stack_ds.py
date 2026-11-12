class AuditStack:
    def __init__(self):
        self._events = []
        
    def push(self, event):
        self._events.append(event)

    def pop(self):
        if not self._events:
            raise IndexError("Audit stack is empty - nothing to undo")
        return self._events.pop()

    def peek(self):
        if not self._events:
            raise IndexError("Audit stack is empty")
        return self._events[-1]

    def get_all_events(self):
        """Newest first."""
        return list(reversed(self._events))

    def size(self):
        return len(self._events)

    def is_empty(self):
        return not self._events
