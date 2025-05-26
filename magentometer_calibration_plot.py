import numpy as np

# Load the CSV file
data = np.genfromtxt('adc_data.csv', delimiter=',', names=True, dtype=None, encoding='utf-8')

# Access columns
timestamps = data['Timestamp']
x = data['X']
y = data['Y']
z = data['Z']

# Create 3d scatter plot and use colorbar to indicate magnitude
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D


fig = plt.figure()
ax = fig.add_subplot(111, projection='3d')
magnitude = np.sqrt(x**2 + y**2 + z**2)
sc = ax.scatter(x, y, z, c=magnitude, cmap='viridis', marker='o')
plt.colorbar(sc, label='Magnitude')
ax.set_xlabel('X')
ax.set_ylabel('Y')
ax.set_zlabel('Z')
ax.set_title('Magnetometer Calibration Data')
#plt.show()

# create 2d scatter plot for each axis and use color to indicate magnitude and plot together
fig, axs = plt.subplots(1, 3, figsize=(15, 5))
axs[0].scatter(x, y, c=magnitude, cmap='viridis', marker='o')
axs[0].set_xlabel('X')
axs[0].set_ylabel('Y')
axs[0].set_title('XY Plane')
axs[1].scatter(x, z, c=magnitude, cmap='viridis', marker='o')
axs[1].set_xlabel('X')
axs[1].set_ylabel('Z')
axs[1].set_title('XZ Plane')
axs[2].scatter(y, z, c=magnitude, cmap='viridis', marker='o')
axs[2].set_xlabel('Y')
axs[2].set_ylabel('Z')
axs[2].set_title('YZ Plane')
plt.tight_layout()
plt.show()

