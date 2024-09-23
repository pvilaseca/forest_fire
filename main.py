# main.py

from js import document, console, setInterval, clearInterval
from pyodide.ffi import create_proxy, to_js
import numpy as np
from enum import Enum

# Import Chart.js through Pyodide
from js import Chart

# Define TileState Enum
class TileState(Enum):
    EMPTY = 0
    TREE = 1
    FIRE = 2
    ASHES = 3

# Define Forest class
class Forest:
    def __init__(self, size):
        self.size = size
        self.grid = np.full((size, size), TileState.EMPTY, dtype=object)

    def plant_trees(self, num_trees):
        available_positions = [(i, j) for i in range(self.size) for j in range(self.size)]
        np.random.shuffle(available_positions)
        for i, (row, col) in enumerate(available_positions):
            if i >= num_trees:
                break
            self.grid[row][col] = TileState.TREE

    def ignite_tree(self):
        tree_positions = list(zip(*np.where(self.grid == TileState.TREE)))
        if tree_positions:
            row, col = tree_positions[np.random.choice(len(tree_positions))]
            self.grid[row][col] = TileState.FIRE

    def get_state(self, row, col):
        return self.grid[row % self.size][col % self.size]

    def set_state(self, row, col, state):
        self.grid[row % self.size][col % self.size] = state

# Define Simulation class
class Simulation:
    def __init__(self, forest):
        self.forest = forest
        self.time_step = 0

    def next_step(self):
        new_grid = self.forest.grid.copy()
        size = self.forest.size

        for row in range(size):
            for col in range(size):
                current_state = self.forest.get_state(row, col)

                if current_state == TileState.FIRE:
                    new_grid[row][col] = TileState.ASHES

                    neighbors = [(-1, 0), (1, 0), (0, -1), (0, 1)]
                    for dr, dc in neighbors:
                        nr, nc = row + dr, col + dc
                        if 0 <= nr < size and 0 <= nc < size:
                            neighbor_state = self.forest.get_state(nr, nc)
                            if neighbor_state == TileState.TREE:
                                new_grid[nr][nc] = TileState.FIRE

        self.forest.grid = new_grid
        self.time_step += 1

        # Update statistics
        total_trees = np.count_nonzero(self.forest.grid == TileState.TREE)
        total_ashes = np.count_nonzero(self.forest.grid == TileState.ASHES)

        # Update the chart
        update_chart(self.time_step, total_trees, total_ashes)

    def has_fire(self):
        return np.any(self.forest.grid == TileState.FIRE)

# Define Visualization class
class Visualization:
    def __init__(self, forest):
        self.forest = forest
        self.canvas = document.getElementById("grid-canvas")
        self.context = self.canvas.getContext("2d")

    def draw_grid(self):
        size = self.forest.size
        cell_size = self.canvas.width / size

        for row in range(size):
            for col in range(size):
                state = self.forest.get_state(row, col)

                if state == TileState.EMPTY:
                    color = "black"
                elif state == TileState.TREE:
                    color = "green"
                elif state == TileState.FIRE:
                    color = "red"
                elif state == TileState.ASHES:
                    color = "grey"
                else:
                    color = "black"

                self.context.fillStyle = color
                self.context.fillRect(col * cell_size, row * cell_size, cell_size, cell_size)

# Initialize Chart.js Chart
chart = None

def initialize_chart():
    global chart
    ctx = document.getElementById("simulation-chart").getContext("2d")

    config = {
        "type": "line",
        "data": {
            "labels": [],
            "datasets": [
                {
                    "label": "Trees Left",
                    "data": [],
                    "borderColor": "green",
                    "fill": False,
                },
                {
                    "label": "Trees Burned",
                    "data": [],
                    "borderColor": "red",
                    "fill": False,
                },
            ],
        },
        "options": {
            "responsive": True,
            "maintainAspectRatio": False,
            "animation": False,
            "scales": {
                "xAxes": [{
                    "scaleLabel": {
                        "display": True,
                        "labelString": "Time Steps"
                    }
                }],
                "yAxes": [{
                    "scaleLabel": {
                        "display": True,
                        "labelString": "Number of Trees"
                    }
                }]
            }
        }
    }

    # Convert the config dictionary to a JavaScript object
    config_js = to_js(config, dict_converter=js.Object.fromEntries)

    chart = Chart.new(ctx, config_js)

def update_chart(time_step, trees_left, trees_burned):
    global chart
    if chart:
        chart.data.labels.push(time_step)
        chart.data.datasets[0].data.push(trees_left)
        chart.data.datasets[1].data.push(trees_burned)
        chart.update()

# Global instances
forest = None
simulation = None
visualization = None
is_running = False
interval_id = None

# Event handlers
def generate_forest(event=None):
    global forest, simulation, visualization, is_running, interval_id, chart

    # If simulation is running, stop it
    if is_running:
        stop_simulation()

    N = int(document.getElementById("grid-size").value)
    Z = int(document.getElementById("num-trees").value)

    forest = Forest(N)
    forest.plant_trees(Z)

    simulation = Simulation(forest)
    visualization = Visualization(forest)

    visualization.draw_grid()

    # Re-initialize the chart
    initialize_chart()

def start_fire(event=None):
    global forest, visualization

    if forest:
        forest.ignite_tree()
        visualization.draw_grid()
    else:
        console.log("Please generate a forest first.")

def next_step(event=None):
    global simulation, visualization

    if simulation:
        simulation.next_step()
        visualization.draw_grid()
    else:
        console.log("Please generate a forest and start the fire first.")

def run_simulation(event=None):
    global is_running, interval_id, simulation, visualization

    if not simulation:
        console.log("Please generate a forest and start the fire first.")
        return

    run_button = document.getElementById("run-button")

    if not is_running:
        # Start the simulation
        is_running = True
        run_button.innerHTML = '<i class="fas fa-stop"></i> Stop'

        def step(*args):
            global is_running, interval_id
            if simulation:
                simulation.next_step()
                visualization.draw_grid()

                # Check if there is any fire left
                if not simulation.has_fire():
                    # Stop the simulation automatically
                    stop_simulation()
            else:
                console.log("Simulation has not been initialized.")

        interval_id = setInterval(create_proxy(step), 200)  # 200 milliseconds

    else:
        # Stop the simulation
        stop_simulation()

def stop_simulation():
    global is_running, interval_id

    is_running = False
    run_button = document.getElementById("run-button")
    run_button.innerHTML = '<i class="fas fa-play"></i> Run'

    if interval_id:
        clearInterval(interval_id)
        interval_id = None

# Attach event listeners
document.getElementById("generate-forest").addEventListener("click", create_proxy(generate_forest))
document.getElementById("start-fire").addEventListener("click", create_proxy(start_fire))
document.getElementById("next-step").addEventListener("click", create_proxy(next_step))
document.getElementById("run-button").addEventListener("click", create_proxy(run_simulation))
