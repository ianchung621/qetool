import matplotlib.pyplot as plt
import numpy as np

def get_visible_ylim(ax: plt.Axes, margin: float = 0.05) -> tuple[float, float] | None:
    """
    Compute y-limits based on visible data (within current xlim)
    across all Line2D artists in the given Axes.

    Returns
    -------
    (ymin, ymax) or None if no visible data.
    """
    xmin, xmax = ax.get_xlim()
    y_visible_values = []

    for line in ax.get_lines():
        xdata, ydata = line.get_xdata(), line.get_ydata()
        
        if not isinstance(xdata, np.ndarray):
            xdata = np.asarray(xdata)
        if not isinstance(ydata, np.ndarray):
            ydata = np.asarray(ydata)

        mask = (xdata >= xmin) & (xdata <= xmax)
        y_visible_values.append(ydata[mask])

    if not y_visible_values:
        return None

    y_visible = np.concatenate(y_visible_values)
    ymin, ymax = np.min(y_visible), np.max(y_visible)
    span = ymax - ymin if ymax > ymin else abs(ymax) * 0.1

    return ymin - margin * span, ymax + margin * span