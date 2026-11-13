"""CS1 final project: circuit resistance and current calculator.

Install Drafter:  python -m pip install drafter
Run this file:    python circuit_calculator.py

Five pages: index, circuit_editor, settings, results, guide.
Four action routes: add_resistor, remove_resistor, save_settings, calculate.

Scope: ideal, positive resistors connected entirely in series or parallel.
Resistance is entered in ohms; supply voltage is entered in volts.
Data lasts for the current Drafter session; it is not saved to a database.

Documentation used:
https://drafter-edu.github.io/drafter/reference/components/input/selectbox/
https://drafter-edu.github.io/drafter/reference/components/input/checkbox/
https://drafter-edu.github.io/drafter/reference/components/data/table/

AI assisted with this starter. Keep the conversation for the assignment's
LLM disclosure, and review the code and explanations before submission.
"""

from dataclasses import dataclass
from math import isfinite

from drafter import *


@dataclass
class Resistor:
    """One resistor, identified by a unique name rather than its position."""

    name: str
    resistance: float


@dataclass
class State:
    """All changing application data belongs here, not in global variables."""

    resistors: list[Resistor]
    circuit_type: str
    voltage: float
    show_steps: bool
    feedback: str


# ---------- Helpers: ordinary functions, not additional page routes ----------

def valid_number(text: str) -> bool:
    """Check text before converting it to a number in an action route.

    try/except handles a ValueError from float(), such as float('hello'),
    so invalid input produces feedback instead of crashing the app.
    isfinite() rejects special values such as nan and infinity.
    """
    try:
        number = float(text)
    except ValueError:
        return False
    return isfinite(number)


def equivalent_resistance(resistors: list[Resistor], circuit_type: str) -> float:
    """Calculate resistance for a nonempty list of positive resistors."""
    total = 0.0
    if circuit_type == "Series":
        for resistor in resistors:
            total = total + resistor.resistance
        return total

    # Parallel formula: first sum 1/R for every resistor, then take 1/sum.
    # The loop meaningfully reads an attribute of each dataclass instance.
    for resistor in resistors:
        total = total + 1.0 / resistor.resistance
    return 1.0 / total


def apply_settings(state: State, circuit_type: str,
                   voltage: str, show_steps: bool) -> bool:
    """Validate the entire form before changing the saved settings."""
    if circuit_type != "Series" and circuit_type != "Parallel":
        state.feedback = "Choose Series or Parallel."
        return False
    if not valid_number(voltage):
        state.feedback = "Enter a valid number for the supply voltage."
        return False
    if float(voltage) < 0:
        state.feedback = "Supply voltage must be zero or greater."
        return False

    state.circuit_type = circuit_type
    state.voltage = float(voltage)
    state.show_steps = show_steps
    return True


# ---------- Page 1: home ----------

@route
def index(state: State) -> Page:
    return Page(state, [
        Header("Circuit Resistance and Current Calculator"),
        "Build a circuit, choose series or parallel, and find its total "
        "resistance and current.\n",
        "Use resistance values in ohms and voltage in volts.\n",
        "This calculator assumes ideal resistors and wires.\n",
        Button("Start building a circuit", circuit_editor),
        Button("Read the guide", guide),
    ])


# ---------- Page 2: add, list, and remove resistors ----------

@route
def circuit_editor(state: State) -> Page:
    content = [
        Header("Build Your Circuit"),
        state.feedback + "\n",
        "Number of resistors: " + str(len(state.resistors)) + "\n",
    ]
    if len(state.resistors) == 0:
        content.append("No resistors added yet.\n")
    else:
        content.append(Table(state.resistors, ["Name", "Resistance (ohms)"]))

    content.extend([
        Header("Add a resistor", 2),
        "Resistor name (for example R1):\n",
        TextBox("resistor_name", ""),
        "Resistance in ohms (for example 100):\n",
        TextBox("resistance", ""),
        Button("Add resistor", add_resistor),
        Header("Remove a resistor", 2),
        "Enter the resistor name to remove:\n",
        TextBox("remove_name", ""),
        Button("Remove resistor", remove_resistor),
        "Names are unique. Capitalization does not matter.\n",
        Button("Continue to settings", settings),
        Button("Home", index),
    ])
    return Page(state, content)


@route
def add_resistor(state: State, resistor_name: str, resistance: str) -> Page:
    # strip() removes surrounding spaces, and upper() normalizes names.
    name = resistor_name.strip().upper()
    if name == "":
        state.feedback = "Enter a name for the resistor."
        return circuit_editor(state)
    if not valid_number(resistance):
        state.feedback = "Enter a valid number for resistance."
        return circuit_editor(state)
    if float(resistance) <= 0:
        state.feedback = "Resistance must be greater than zero ohms."
        return circuit_editor(state)

    for resistor in state.resistors:
        if resistor.name == name:
            state.feedback = "That resistor name already exists. Choose another name."
            return circuit_editor(state)

    state.resistors.append(Resistor(name, float(resistance)))
    state.feedback = "Added " + name + "."
    return circuit_editor(state)


@route
def remove_resistor(state: State, remove_name: str) -> Page:
    name = remove_name.strip().upper()
    if name == "":
        state.feedback = "Enter the name of the resistor to remove."
        return circuit_editor(state)

    # Build a replacement list so the loop does not modify the list it visits.
    # Removing an earlier resistor does not change the other resistors' names.
    remaining = []
    found = False
    for resistor in state.resistors:
        if resistor.name == name:
            found = True
        else:
            remaining.append(resistor)

    if found:
        state.resistors = remaining
        state.feedback = "Removed " + name + "."
    else:
        state.feedback = "No resistor named " + name + " was found."
    return circuit_editor(state)


# ---------- Page 3: circuit settings ----------

@route
def settings(state: State) -> Page:
    return Page(state, [
        Header("Circuit Settings"),
        state.feedback + "\n",
        "Connection type:\n",
        SelectBox("circuit_type", ["Series", "Parallel"], state.circuit_type),
        "Supply voltage in volts:\n",
        TextBox("voltage", str(state.voltage)),
        CheckBox("show_steps", state.show_steps),
        " Show calculation steps\n",
        Button("Save settings", save_settings),
        Button("Calculate resistance and current", calculate),
        "Save settings or Calculate applies this form.\n",
        Button("Back to resistors", circuit_editor),
        Button("Home", index),
    ])


@route
def save_settings(state: State, circuit_type: str,
                  voltage: str, show_steps: bool) -> Page:
    if apply_settings(state, circuit_type, voltage, show_steps):
        state.feedback = "Settings saved."
    return settings(state)


@route
def calculate(state: State, circuit_type: str,
              voltage: str, show_steps: bool) -> Page:
    # Use the current form, even if the user has not clicked Save settings.
    if not apply_settings(state, circuit_type, voltage, show_steps):
        return settings(state)
    if len(state.resistors) == 0:
        state.feedback = "Add at least one resistor before calculating."
        return circuit_editor(state)
    state.feedback = ""
    return results(state)


# ---------- Page 4: results ----------

@route
def results(state: State) -> Page:
    if len(state.resistors) == 0:
        state.feedback = "Add at least one resistor before viewing results."
        return circuit_editor(state)

    # Recompute from current State; never keep a stale result after editing.
    total = equivalent_resistance(state.resistors, state.circuit_type)
    if not isfinite(total) or total <= 0:
        state.feedback = "Those values are outside the calculator's numeric range."
        return circuit_editor(state)
    current = state.voltage / total
    if not isfinite(current):
        state.feedback = "Those values produce a current too large to calculate."
        return settings(state)

    # format(value, '.6g') shows six significant digits without changing
    # the underlying calculation. Small nonzero results stay visible.
    content = [
        Header("Calculation Results"),
        "Connection: " + state.circuit_type + "\n",
        "Resistor count: " + str(len(state.resistors)) + "\n",
        Table(state.resistors, ["Name", "Resistance (ohms)"]),
        "Supply voltage: " + format(state.voltage, ".6g") + " V\n",
        "Total resistance: " + format(total, ".6g") + " ohms\n",
        "Total current: " + format(current, ".6g") + " A\n",
    ]
    if state.show_steps:
        content.append(Header("Calculation steps", 2))
        terms = []
        for resistor in state.resistors:
            value = format(resistor.resistance, ".6g")
            if state.circuit_type == "Series":
                terms.append(value)
            else:
                terms.append("1/" + value)

        # join() connects the text terms with ' + ' for a readable formula.
        if state.circuit_type == "Series":
            content.append("R_total = " + " + ".join(terms) + " ohms\n")
        else:
            content.append("R_total = 1 / (" + " + ".join(terms) + ") ohms\n")
        content.append(
            "I_total = V / R_total = " + format(state.voltage, ".6g")
            + " / " + format(total, ".6g") + " = "
            + format(current, ".6g") + " A\n"
        )

    content.extend([
        Button("Edit resistors", circuit_editor),
        Button("Change settings", settings),
        Button("Open the guide", guide),
        Button("Home", index),
    ])
    return Page(state, content)


# ---------- Page 5: guide ----------

@route
def guide(state: State) -> Page:
    return Page(state, [
        Header("Circuit Calculation Guide"),
        Header("How to use the calculator", 2),
        "1. Add each resistor using a unique name and a positive ohm value.\n",
        "2. Remove a resistor by its name if needed.\n",
        "3. Select Series or Parallel and enter the supply voltage.\n",
        "4. Click Calculate to view total resistance and total current.\n",
        Header("Series circuits", 2),
        "Resistors connect one after another in a single path.\n",
        "R_total = R1 + R2 + ...\n",
        "Two 100 ohm resistors have a total resistance of 200 ohms.\n",
        Header("Parallel circuits", 2),
        "Each resistor is a separate branch across the same two nodes.\n",
        "R_total = 1 / (1/R1 + 1/R2 + ...)\n",
        "Two 100 ohm resistors have a total resistance of 50 ohms.\n",
        Header("Total current and units", 2),
        "Ohm's law: I_total = V / R_total. Current is measured in amps (A).\n",
        "At 10 V, the series example draws 0.05 A and the parallel example "
        "draws 0.2 A from the supply.\n",
        "Enter ohms, not kilo-ohms: 1 kilo-ohm = 1000 ohms.\n",
        "Zero supply voltage is allowed and gives zero current.\n",
        "Assumptions: ideal resistors and wires, positive resistance values, "
        "and entirely series or entirely parallel connections.\n",
        Button("Build a circuit", circuit_editor),
        Button("Home", index),
    ])


# This guard starts the website only when running this file directly.
# Importing the file for calculation tests does not start a server.
if __name__ == "__main__":
    start_server(State([], "Series", 10.0, True, ""))

