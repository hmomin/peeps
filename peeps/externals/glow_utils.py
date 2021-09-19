from collections import deque
from constants import ev, EASE_IN_OUT
from externals.bezier_interpolation import interpolate
from externals.iterable_utils import flatten

def toggleGlow():
    """
    Turns bloom (glow) on or off.
    """
    if ev.use_bloom:
        ev.use_bloom = False
    else:
        ev.use_bloom = True
        ev.bloom_threshold = 0
        ev.bloom_knee = 0.5
        ev.bloom_radius = 6.5
        ev.bloom_color = (1, 1, 1)
        ev.bloom_intensity = 0.1
        ev.bloom_clamp = 0

def glowOn(intensity=0.1):
    """Turns bloom (glow) on.

    Args:
        intensity (float, optional): intensity of bloom. Defaults to 0.1.
    """
    if not ev.use_bloom:
        toggleGlow()
    ev.bloom_intensity = intensity
def init_glowOn(t0=0, tf=1, rate=EASE_IN_OUT, intensity=0.1):
    t = interpolate(t0, tf, rate)
    t.pop(0)
    intensityVals = interpolate(0, intensity, rate, len(t))
    intensityVals.reverse()
    return deque(intensityVals)
def update_glowOn(val, intensity=0.1):
    glowOn(val)

def flickerGlow(intensity=0.05):
    """
    Flickers bloom (glow) between its current intensity and the provided intensity.

    Args:
        intensity (float, optional): intensity to flicker towards. Defaults to 0.05.
    """
    if not ev.use_bloom:
        toggleGlow()
    ev.bloom_intensity = intensity
def init_flickerGlow(t0=0, tf=1, rate=EASE_IN_OUT, intensity=0.05):
    currentIntensity = ev.bloom_intensity
    t = interpolate(t0, tf, rate)
    t.pop(0)
    onVals = interpolate(currentIntensity, intensity, rate, len(t) / 2)
    onVals.pop()
    offVals = onVals.copy()
    onVals.reverse()
    return deque(flatten([offVals, onVals]))
def update_flickerGlow(val, intensity=0.05):
    flickerGlow(val)
