class ExponentialMovingAverageSingleValue:
    """Exponential Moving Average (EMA) filter."""

    def __init__(self, alpha):
        self.alpha = alpha
        self.previous_value = 0

    def update(self, input_value):
        # print(input_value)
        # Calculate EMA by weighting current value with alpha
        # and previous value with (1 - alpha)
        ema_value = self.alpha * input_value + (1 - self.alpha) * self.previous_value
        self.previous_value = ema_value
        baseline = max(0, input_value - ema_value)
        return baseline


class ExponentialMovingAverage:
    """Exponential Moving Average (EMA) filter."""

    def __init__(self, alpha=0.5):
        self.alpha = alpha
        self.previous_values = [
            0,
            0,
            0,
            0,
        ]

    def update(self, input_values):
        """Update ema filter.

        Calculate EMA by weighting current value with alpha
        and previous value with (1 - alpha)
        """
        ema_values = []
        baseline_values = []
        for i in range(len(input_values)):
            current_value = input_values[i]
            previous_value = self.previous_values[i]
            ema_value = (
                self.alpha * current_value + (1 - self.alpha) * previous_value
            )
            self.previous_values[i] = ema_value
            baseline_values.append(max(0, current_value - ema_value))
        return baseline_values
