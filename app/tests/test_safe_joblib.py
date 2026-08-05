import pytest
import io
import pickle
import numpy as np
import joblib
import tempfile
import os

from app.core.safe_joblib import RestrictedUnpickler, safe_load, safe_load_buffer


class TestRestrictedUnpickler:
    def test_allows_numpy(self):
        data = np.array([1, 2, 3])
    def test_allows_sklearn(self):
        from sklearn.linear_model import LogisticRegression
        model = LogisticRegression()
        unpickler = RestrictedUnpickler.__new__(RestrictedUnpickler)
        result = unpickler.find_class('sklearn.linear_model', 'LogisticRegression')
        assert result == LogisticRegression

    def test_blocks_os_system(self):
        unpickler = RestrictedUnpickler.__new__(RestrictedUnpickler)
        with pytest.raises(pickle.UnpicklingError, match="Blocked"):
            unpickler.find_class('os', 'system')

    def test_blocks_subprocess(self):
        unpickler = RestrictedUnpickler.__new__(RestrictedUnpickler)
        with pytest.raises(pickle.UnpicklingError, match="Blocked"):
            unpickler.find_class('subprocess', 'run')

    def test_allows_collections_ordereddict(self):
        unpickler = RestrictedUnpickler.__new__(RestrictedUnpickler)
        result = unpickler.find_class('collections', 'OrderedDict')
        from collections import OrderedDict
        assert result == OrderedDict

    def test_blocks_eval(self):
        unpickler = RestrictedUnpickler.__new__(RestrictedUnpickler)
        with pytest.raises(pickle.UnpicklingError, match="Blocked"):
            unpickler.find_class('builtins', 'eval')


class TestSafeLoad:
    def test_load_numpy_array(self):
        data = np.array([1.0, 2.0, 3.0])
        with tempfile.NamedTemporaryFile(suffix='.joblib', delete=False) as f:
            joblib.dump(data, f.name)
            filepath = f.name
        try:
            loaded = safe_load(filepath)
            np.testing.assert_array_equal(loaded, data)
        finally:
            os.unlink(filepath)

    def test_load_sklearn_model(self):
        from sklearn.linear_model import LogisticRegression
        model = LogisticRegression()
        X = np.array([[1, 2], [3, 4], [5, 6], [7, 8]])
        y = np.array([0, 0, 1, 1])
        model.fit(X, y)
        with tempfile.NamedTemporaryFile(suffix='.joblib', delete=False) as f:
            joblib.dump(model, f.name)
            filepath = f.name
        try:
            loaded = safe_load(filepath)
            assert hasattr(loaded, 'predict')
            preds = loaded.predict(X)
            assert len(preds) == 4
        finally:
            os.unlink(filepath)

    def test_load_dict(self):
        data = {'key': 'value', 'numbers': [1, 2, 3]}
        with tempfile.NamedTemporaryFile(suffix='.joblib', delete=False) as f:
            joblib.dump(data, f.name)
            filepath = f.name
        try:
            loaded = safe_load(filepath)
            assert loaded == data
        finally:
            os.unlink(filepath)


class TestSafeLoadBuffer:
    def test_load_from_bytes(self):
        data = np.array([10, 20, 30])
        buf = io.BytesIO()
        joblib.dump(data, buf)
        loaded = safe_load_buffer(buf.getvalue())
        np.testing.assert_array_equal(loaded, data)

    def test_load_dict_buffer(self):
        data = {'a': 1, 'b': 2}
        buf = io.BytesIO()
        joblib.dump(data, buf)
        loaded = safe_load_buffer(buf.getvalue())
        assert loaded == data

    def test_rejects_garbage_buffer(self):
        with pytest.raises(Exception):
            safe_load_buffer(b"this is not a valid joblib file")
