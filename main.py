"""CS1 final project: circuit resistance and current calculator.

Install Drafter:  python -m pip install drafter
Run this file:    python circuit_calculator.py
Tests run automatically before the website starts.

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

from bakery import assert_equal as assert_equals
from dataclasses import dataclass
from math import isfinite
from html import escape

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


def diagram_text(x: int, y: int, label: str) -> str:
    """Wrap a label into 24-character lines without losing its full name.

    Slicing selects each chunk. escape() converts characters such as < and &
    into safe text so resistor names cannot turn into SVG markup.
    f-strings insert coordinates into the drawing, not executable Python.
    """
    drawing = ""
    for start in range(0, len(label), 24):
        line = escape(label[start:start + 24])
        drawing = drawing + (
            f'<text x="{x}" y="{y}" fill="#25364a" '
            f'font-family="Arial, sans-serif" font-size="16">{line}</text>'
        )
        y = y + 22
    return drawing


def circuit_diagram(state: State):
    """Draw every stored resistor, using its actual name and resistance.

    SVG is drawing markup. M moves a pen, H/V draw horizontal/vertical wires,
    rect draws a resistor, and circle draws the DC supply. These are generated
    from State each time the editor is shown, so adding/removing updates them.

    Series uses one vertical chain and a return wire. Rotating the familiar
    horizontal resistor layout keeps any number of resistors readable.
    Parallel uses two rails and one branch per resistor.
    Coordinates grow with the number of labels; longer names get more space.
    Div is an HTML container. Its CSS limits visible height and enables
    scrolling, keeping 100-resistor diagrams and the form usable together.
    """
    if len(state.resistors) == 0:
        return Div("Add a resistor to see your circuit diagram.")

    wires = ""
    symbols = ""
    labels = ""
    y = 100
    previous_wire_end = 60

    for resistor in state.resistors:
        # Integer division rounds up the number of 24-character name lines.
        name_lines = (len(resistor.name) + 23) // 24
        value = format(resistor.resistance, ".6g") + " ohms"
        if state.circuit_type == "Series":
            wires = wires + f'<path d="M360 {previous_wire_end} V{y - 20}"/>'
            symbols = symbols + (
                f'<rect x="345" y="{y - 20}" width="30" height="40"/>'
            )
            labels = labels + diagram_text(410, y - 5, resistor.name)
            labels = labels + diagram_text(410, y - 5 + name_lines * 22, value)
            previous_wire_end = y + 20
        else:
            wires = wires + (
                f'<path d="M220 {y} H350 M450 {y} H600"/>'
            )
            symbols = symbols + (
                f'<rect x="350" y="{y - 15}" width="100" height="30"/>'
            )
            # Dots identify where each branch joins the two shared rails.
            symbols = symbols + (
                f'<circle cx="220" cy="{y}" r="4" fill="#25364a"/>'
                f'<circle cx="600" cy="{y}" r="4" fill="#25364a"/>'
            )
            labels = labels + diagram_text(300, y + 36, resistor.name)
            labels = labels + diagram_text(300, y + 36 + name_lines * 22, value)

        # max() ensures enough room for long names and the next resistor.
        y = y + max(120, name_lines * 22 + 80)

    bottom = y - 40
    if state.circuit_type == "Series":
        wires = wires + (
            f'<path d="M100 115 V60 H360 M360 {previous_wire_end} '
            f'V{bottom} H100 V165"/>'
        )
    else:
        wires = wires + (
            f'<path d="M100 115 V60 H220 V{bottom} H100 V165 '
            f'M600 60 V{bottom}"/>'
        )

    labels = labels + diagram_text(145, 140, "Supply")
    labels = labels + diagram_text(145, 163, format(state.voltage, ".6g") + " V")
    # Escape every label derived from user data before placing it in markup.
    title = escape(state.circuit_type + " circuit with "
                   + str(len(state.resistors)) + " resistors")
    drawing = (
        "<title>" + title + "</title>"
        "<desc>Each resistor is labeled with its stored name and resistance "
        "in ohms. The supply voltage is shown beside the source.</desc>"
        '<g fill="none" stroke="#25364a" stroke-width="3">' + wires + '</g>'
        '<g fill="#eef4fa" stroke="#25364a" stroke-width="3">' + symbols + '</g>'
        '<circle cx="100" cy="140" r="25" fill="white" '
        'stroke="#25364a" stroke-width="3"/>'
        '<text x="100" y="138" text-anchor="middle" font-size="19">+</text>'
        '<text x="100" y="158" text-anchor="middle" font-size="19">-</text>'
        + labels
    )
    height = bottom + 40
    # Match display height to viewBox so large circuits scroll instead of
    # being scaled down into tiny, unreadable symbols.
    image = SVG(drawing, width=640, height=int(height * 640 / 720),
                viewBox="0 0 720 " + str(height))
    return Div(image, style="max-height: 520px; overflow: auto; "
               "border: 1px solid #d9e1e8; padding: 8px;")


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
        Header("Circuit diagram", 2),
        "Saved connection type: " + state.circuit_type + "\n",
        circuit_diagram(state),
        "The diagram shows your stored resistors. "
        "Scroll inside it to see larger circuits.\n",
        "Change the circuit type in Settings, save it, then return here.\n",
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


# ---------- Equality tests ----------
# Bakery names its helper assert_equal; "as assert_equals" above gives it
# the requested local name. Decimal comparisons use Bakery's tolerance.
# These functions use local State objects so they do not change a user's circuit.
# They are ordinary functions, not Drafter routes, and run before startup.

def test_valid_number():
    assert_equals(valid_number("100"), True)
    assert_equals(valid_number("12.5"), True)
    assert_equals(valid_number("0"), True)
    assert_equals(valid_number("-10"), True)  # Numeric; action routes check ranges.
    assert_equals(valid_number(" 220 "), True)
    assert_equals(valid_number(""), False)
    assert_equals(valid_number("hello"), False)
    assert_equals(valid_number("100 ohms"), False)
    assert_equals(valid_number("nan"), False)
    assert_equals(valid_number("inf"), False)
    assert_equals(valid_number("-inf"), False)


def test_equivalent_resistance():
    pair = [Resistor("R1", 100.0), Resistor("R2", 100.0)]
    assert_equals(equivalent_resistance(pair, "Series"), 200.0)
    assert_equals(equivalent_resistance(pair, "Parallel"), 50.0)
    different = [Resistor("R1", 100.0), Resistor("R2", 200.0)]
    assert_equals(equivalent_resistance(different, "Series"), 300.0)
    assert_equals(equivalent_resistance(different, "Parallel"), 66.6666666667)
    single = [Resistor("R1", 220.0)]
    assert_equals(equivalent_resistance(single, "Series"), 220.0)
    assert_equals(equivalent_resistance(single, "Parallel"), 220.0)
    many = []
    for number in range(100):
        many.append(Resistor("R" + str(number + 1), 100.0))
    assert_equals(equivalent_resistance(many, "Series"), 10000.0)
    assert_equals(equivalent_resistance(many, "Parallel"), 1.0)
    # Empty and nonpositive lists are rejected by routes before this helper.


def test_add_resistor():
    state = State([], "Series", 10.0, True, "")
    page = add_resistor(state, " r1 ", "100")
    assert_equals(state.resistors, [Resistor("R1", 100.0)])
    assert_equals(page.state, state)
    assert_equals(Header("Build Your Circuit") in page.content, True)
    add_resistor(state, "R2", "220")
    assert_equals(state.resistors, [Resistor("R1", 100.0), Resistor("R2", 220.0)])
    # A duplicate name, even with a different case, must not add an object.
    add_resistor(state, "r1", "330")
    assert_equals(len(state.resistors), 2)
    assert_equals("already exists" in state.feedback, True)
    for invalid_value in ["0", "-1", "hello", "", "nan", "inf"]:
        add_resistor(state, "R3", invalid_value)
        assert_equals(len(state.resistors), 2)
    add_resistor(state, "   ", "100")
    assert_equals(len(state.resistors), 2)


def test_remove_resistor():
    state = State([Resistor("R1", 100.0), Resistor("R2", 220.0),
                   Resistor("R3", 330.0)], "Series", 10.0, True, "")
    page = remove_resistor(state, " r2 ")
    assert_equals(state.resistors, [Resistor("R1", 100.0), Resistor("R3", 330.0)])
    assert_equals(page.state, state)
    remove_resistor(state, "MISSING")
    assert_equals(len(state.resistors), 2)
    assert_equals("was found" in state.feedback, True)
    remove_resistor(state, "")
    assert_equals(len(state.resistors), 2)
    remove_resistor(state, "R1")
    remove_resistor(state, "R3")
    assert_equals(state.resistors, [])
    remove_resistor(state, "R1")
    assert_equals(state.resistors, [])


def test_settings():
    state = State([], "Series", 10.0, True, "")
    assert_equals(apply_settings(state, "Parallel", "12", False), True)
    assert_equals(state.circuit_type, "Parallel")
    assert_equals(state.voltage, 12.0)
    assert_equals(state.show_steps, False)
    for bad_voltage in ["-1", "bad", "", "nan", "inf"]:
        assert_equals(apply_settings(state, "Series", bad_voltage, True), False)
        assert_equals(state.circuit_type, "Parallel")
        assert_equals(state.voltage, 12.0)
        assert_equals(state.show_steps, False)
    assert_equals(apply_settings(state, "Mixed", "10", True), False)
    assert_equals(state.circuit_type, "Parallel")
    page = save_settings(state, "Series", "0", True)
    assert_equals(state.voltage, 0.0)
    assert_equals(state.circuit_type, "Series")
    assert_equals(state.show_steps, True)
    assert_equals(Header("Circuit Settings") in page.content, True)
    save_settings(state, "Series", "-5", False)
    assert_equals(state.voltage, 0.0)
    assert_equals(state.show_steps, True)


def test_calculate_and_results():
    state = State([Resistor("R1", 100.0), Resistor("R2", 100.0)],
                  "Series", 10.0, True, "")
    page = calculate(state, "Series", "10", True)
    assert_equals("Total resistance: 200 ohms\n" in page.content, True)
    assert_equals("Total current: 0.05 A\n" in page.content, True)
    assert_equals(Header("Calculation steps", 2) in page.content, True)
    # Calculate must apply unsaved form settings before computing totals.
    page = calculate(state, "Parallel", "10", False)
    assert_equals(state.circuit_type, "Parallel")
    assert_equals(state.show_steps, False)
    assert_equals("Total resistance: 50 ohms\n" in page.content, True)
    assert_equals("Total current: 0.2 A\n" in page.content, True)
    assert_equals(Header("Calculation steps", 2) in page.content, False)
    page = calculate(state, "Parallel", "0", True)
    assert_equals("Total current: 0 A\n" in page.content, True)
    # Reopening results after changing resistors must recompute the answer.
    remove_resistor(state, "R2")
    page = results(state)
    assert_equals("Total resistance: 100 ohms\n" in page.content, True)
    assert_equals(len(state.resistors), 1)
    page = calculate(state, "Series", "bad", True)
    assert_equals(Header("Circuit Settings") in page.content, True)
    assert_equals(state.voltage, 0.0)
    empty = State([], "Series", 10.0, True, "")
    page = calculate(empty, "Series", "10", True)
    assert_equals(Header("Build Your Circuit") in page.content, True)
    assert_equals("at least one" in empty.feedback, True)
    page = results(empty)
    assert_equals(Header("Build Your Circuit") in page.content, True)


def test_pages():
    state = State([], "Series", 10.0, True, "")
    assert_equals(Header("Circuit Resistance and Current Calculator") in index(state).content, True)
    assert_equals(Header("Build Your Circuit") in circuit_editor(state).content, True)
    assert_equals(Header("Circuit Settings") in settings(state).content, True)
    assert_equals(Header("Circuit Calculation Guide") in guide(state).content, True)
    assert_equals(isinstance(guide(state), Page), True)


def test_diagrams():
    # diagram_text must display names safely, not interpret them as markup.
    label = diagram_text(10, 20, "R<1>&")
    assert_equals("R&lt;1&gt;&amp;" in label, True)
    assert_equals("<1>" in label, False)
    assert_equals(diagram_text(10, 20, "A" * 50).count("<text "), 3)
    empty = State([], "Series", 10.0, True, "")
    assert_equals("Add a resistor" in circuit_diagram(empty).content[0], True)
    for connection in ["Series", "Parallel"]:
        state = State([Resistor("R1", 100.0), Resistor("R2", 220.0)],
                      connection, 12.0, True, "")
        # The diagram Div contains an SVG; its content is the drawing text.
        drawing = circuit_diagram(state).content[0].content
        assert_equals(drawing.count("<rect "), 2)
        assert_equals("R1" in drawing, True)
        assert_equals("R2" in drawing, True)
        assert_equals("100 ohms" in drawing, True)
        assert_equals("220 ohms" in drawing, True)
        assert_equals("12 V" in drawing, True)
        remove_resistor(state, "R1")
        drawing = circuit_diagram(state).content[0].content
        assert_equals(drawing.count("<rect "), 1)
        assert_equals("R1" in drawing, False)
        assert_equals("R2" in drawing, True)
        add_resistor(state, "R3", "330")
        drawing = circuit_diagram(state).content[0].content
        assert_equals(drawing.count("<rect "), 2)
        assert_equals("330 ohms" in drawing, True)
        many = []
        for number in range(100):
            many.append(Resistor("R" + str(number + 1), 100.0))
        state.resistors = many
        drawing = circuit_diagram(state).content[0].content
        assert_equals(drawing.count("<rect "), 100)
        assert_equals("R100" in drawing, True)


def run_tests():
    test_valid_number()
    test_equivalent_resistance()
    test_add_resistor()
    test_remove_resistor()
    test_settings()
    test_calculate_and_results()
    test_pages()
    test_diagrams()


# The main guard prevents tests and website startup when imported.
# Running this file checks the functions first, then starts a fresh circuit.
# Tests use their own local State objects and do not fill the website's list.
if __name__ == "__main__":
    run_tests()
    start_server(State([], "Series", 10.0, True, ""))
