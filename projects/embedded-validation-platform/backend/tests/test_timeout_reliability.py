import subprocess
import sys

import pytest


def test_subprocess_timeout():
    """Verify that a long-running process raises TimeoutExpired."""

    with pytest.raises(subprocess.TimeoutExpired):
        subprocess.run(
            [sys.executable, "-c", "import time; time.sleep(2)"],
            capture_output=True,
            text=True,
            timeout=0.2,
            check=False,
        )
