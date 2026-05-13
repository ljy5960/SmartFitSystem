"""Body-measurement estimation helpers used by training and prediction.

The helpers intentionally depend only on user/body attributes that are
available at prediction time. They must not use the fit label or target class,
otherwise the model can learn leaked target information from imputed features.
"""

HIP_TO_WAIST_RATIO = 1.35
HEIGHT_TO_WAIST_RATIO = 0.43
BRA_BAND_TO_WAIST_OFFSET_CM = 8.0


def is_positive_number(value):
    """Return True when value can be interpreted as a positive float."""
    try:
        return float(value) > 0
    except (TypeError, ValueError):
        return False


def estimate_waist_cm(height_cm=None, size_val=None, bra_num=None, hips_cm=None):
    """Estimate waist circumference from non-label body measurements.

    Priority is given to directly related body measurements. Hips are the most
    informative proxy when present; size, height and bra band are then blended
    as weaker body-shape priors. No fit/target label is used here.
    """
    weighted_estimates = []

    if is_positive_number(hips_cm):
        weighted_estimates.append((float(hips_cm) / HIP_TO_WAIST_RATIO, 4.0))

    if is_positive_number(size_val):
        weighted_estimates.append((float(size_val) * 1.5 + 60.0, 2.0))

    if is_positive_number(height_cm):
        weighted_estimates.append((float(height_cm) * HEIGHT_TO_WAIST_RATIO, 1.5))

    if is_positive_number(bra_num):
        weighted_estimates.append((float(bra_num) * 2.54 - BRA_BAND_TO_WAIST_OFFSET_CM, 1.0))

    if not weighted_estimates:
        return 70.0

    total_weight = sum(weight for _, weight in weighted_estimates)
    return sum(value * weight for value, weight in weighted_estimates) / total_weight


def estimate_hips_cm(waist_cm):
    """Estimate hips circumference from the waist-to-hips relationship."""
    if not is_positive_number(waist_cm):
        return 0.0
    return float(waist_cm) * HIP_TO_WAIST_RATIO