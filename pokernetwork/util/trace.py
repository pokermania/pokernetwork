
import traceback, sys

def format_exc():
    exc_type, exc_value, exc_traceback = sys.exc_info()
    stack = traceback.extract_stack(exc_traceback.tb_frame)[:-1] + traceback.extract_tb(exc_traceback)
    return "\n".join(
        traceback.format_exception_only(exc_type, exc_value) +
        ["Traceback (most recent call first):"] +
        ["  %s:%-3d %s: %s" % t for t in reversed(stack)]
    )
