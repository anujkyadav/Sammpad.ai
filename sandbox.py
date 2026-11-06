"""
sandbox.py
----------
A restricted Python execution sandbox for the student code editor.

NOTE: This is a teaching-grade sandbox (restricted builtins + captured
stdout), suitable for a classroom app run on a trusted local network.
It is NOT a hardened security sandbox -- do not expose this publicly
on the open internet without adding process isolation (e.g. Docker,
a subprocess with resource limits, or a service like Judge0/Piston).
"""

import io
import contextlib
import multiprocessing


SAFE_BUILTINS = {
    "print": print, "range": range, "len": len, "int": int, "float": float,
    "str": str, "list": list, "dict": dict, "tuple": tuple, "set": set,
    "sum": sum, "min": min, "max": max, "sorted": sorted, "enumerate": enumerate,
    "zip": zip, "abs": abs, "round": round, "bool": bool, "input": lambda *_: "",
    "True": True, "False": False, "None": None,
}


def _run_in_subprocess(code: str, queue: multiprocessing.Queue):
    output = io.StringIO()
    try:
        with contextlib.redirect_stdout(output):
            exec(code, {"__builtins__": SAFE_BUILTINS})
        queue.put(("ok", output.getvalue()))
    except Exception as e:
        queue.put(("error", f"{output.getvalue()}\n{type(e).__name__}: {e}"))


def run_code(code: str, timeout_seconds: int = 5) -> dict:
    """
    Runs student code in a separate process with a timeout, so an
    infinite loop in a student's code can't hang the whole app.
    Returns {"status": "ok"|"error"|"timeout", "output": str}
    """
    queue = multiprocessing.Queue()
    proc = multiprocessing.Process(target=_run_in_subprocess, args=(code, queue))
    proc.start()
    proc.join(timeout_seconds)

    if proc.is_alive():
        proc.terminate()
        proc.join()
        return {"status": "timeout", "output": f"Code took longer than {timeout_seconds}s and was stopped."}

    if not queue.empty():
        status, output = queue.get()
        return {"status": status, "output": output}

    return {"status": "error", "output": "No output captured (the process may have crashed)."}
