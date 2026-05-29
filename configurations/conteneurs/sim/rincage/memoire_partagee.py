import threading

class MemoirePartagee:
    def __init__(self, etat_initial):
        self._data = etat_initial.copy()
        self._lock = threading.Lock()

    def get(self, key, default=0):
        with self._lock:
            return self._data.get(key, default)

    def set(self, key, value):
        with self._lock:
            self._data[key] = value

    def get_all(self):
        with self._lock:
            return self._data.copy()