def clamp(val, min, max):
    return max if val > max else min if val < min else val