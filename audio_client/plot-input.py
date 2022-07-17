#!/usr/bin/env python3
"""Plot the live microphone signal(s) with matplotlib.

Matplotlib and NumPy have to be installed.

"""

from matplotlib.animation import FuncAnimation
import matplotlib.pyplot as plt
import numpy as np
from audio_client import Client


c = Client()
c.connect()

samples = 10000

def update_plot(frame):
    """This is called by matplotlib for each plot update.

    Typically, audio callbacks happen more frequently than plot updates,
    therefore the queue tends to contain multiple blocks of audio data.

    """
    lines[0].set_ydata(c.get_window(samples))
    return lines



fig, ax = plt.subplots()
lines = ax.plot(np.zeros(samples))

ax.axis((0, samples, -2**31, 2**31))
ax.set_yticks([0])
ax.yaxis.grid(True)
ax.tick_params(bottom=False, top=False, labelbottom=False,
                right=False, left=False, labelleft=False)
fig.tight_layout(pad=0)
ani = FuncAnimation(fig, update_plot, interval=30, blit=True)
plt.show()
