"""Run this process (and the multiprocessing workers it spawns, which inherit the class) at
BELOW_NORMAL priority, so long searches never steal CPU from the game / fishing bot."""
import sys
def lowprio():
    if sys.platform == "win32":
        import ctypes
        ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x4000)
