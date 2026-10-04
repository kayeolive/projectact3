import os
import shutil
import sys
import textwrap

import requests

GEOCODE_URL = "https://graphhopper.com/api/1/geocode"
ROUTE_URL = "https://graphhopper.com/api/1/route"
key = "c33c968d-e023-4115-a375-c68100819865"

# ---------- user options ---------- added feature to allow the user for their own wanted settings
UNITS = [("km", "Metric (kilometers, km/h)"), ("mi", "Imperial (miles, mph)")]
VEHICLES = [("car", "Drive"), ("bike", "Cycle"), ("foot", "Walk")]
DETAILS = [("summary", "Summary only"),
           ("full", "Summary + step-by-step directions"),
           ("extra", "Summary + directions + extra stats (speed, steps, longest step)")]

settings = {"units": "km", "vehicle": "car", "detail": "full"}

# ---------- colors ---------- added feature to have an upgraded ui 

USE_COLOR = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None
GREEN, RED, YELLOW, CYAN, DIM, BOLD_CYAN = "32", "31", "33", "36", "2", "1;36"


def paint(text, code):
    return "\033[" + code + "m" + text + "\033[0m" if USE_COLOR else text


# ---------- formatting helpers ----------
def label_for(options, value):
    return dict(options)[value]


def format_time(ms):
    """GraphHopper returns time in milliseconds -> HH:MM:SS"""
    seconds = int(ms / 1000)
    return "{:02d}:{:02d}:{:02d}".format(seconds // 3600, (seconds % 3600) // 60, seconds % 60)


def format_dist(meters, units):
    """GraphHopper returns distances in meters."""
    if units == "mi":
        return "{:.2f} mi".format(meters / 1609.344)
    return "{:.2f} km".format(meters / 1000)


def format_speed(meters, ms, units):
    hours = ms / 3600000
    if hours <= 0:
        return "n/a"
    if units == "mi":
        return "{:.1f} mph".format(meters / 1609.344 / hours)
    return "{:.1f} km/h".format(meters / 1000 / hours)


def term_width():
    return min(shutil.get_terminal_size((100, 24)).columns, 110)


def cell(text, width, code=None, align="left"):
    """Pad first, then color, so ANSI codes never break column alignment."""
    padded = text.rjust(width) if align == "right" else text.ljust(width)
    return paint(padded, code) if code else padded


# ---------- API helpers ----------
def geocode(place):
    """Turn a place name into coordinates. Returns (lat, lng, label, status_code, message)."""
    resp = requests.get(GEOCODE_URL, params={"q": place, "limit": 1, "key": key})
    json_data = resp.json()
    if resp.status_code != 200:
        return None, None, None, resp.status_code, json_data.get("message", "")
    if not json_data.get("hits"):
        return None, None, None, 404, "No location found for '" + place + "'."
    hit = json_data["hits"][0]
    label = ", ".join(str(hit[k]) for k in ("name", "state", "country") if hit.get(k))
    return hit["point"]["lat"], hit["point"]["lng"], label, 200, ""


# ---------- settings menu ---------- added feature for users to choose their own settings
def choose(title, options, current):
    """Show a numbered menu; Enter keeps the current value."""
    print("\n" + paint(title, BOLD_CYAN))
    for i, (value, text) in enumerate(options, 1):
        marker = paint(" (current)", DIM) if value == current else ""
        print("  " + str(i) + ") " + text + marker)
    while True:
        answer = input("Choose 1-" + str(len(options)) + " or press Enter to keep: ").strip()
        if answer == "":
            return current
        if answer.isdigit() and 1 <= int(answer) <= len(options):
            return options[int(answer) - 1][0]
        print(paint("Please enter a number from the list.", RED))


def settings_menu():
    settings["units"] = choose("Units", UNITS, settings["units"])
    settings["vehicle"] = choose("Travel mode", VEHICLES, settings["vehicle"])
    settings["detail"] = choose("Data to show", DETAILS, settings["detail"])
    print()
    print_settings()


def print_settings():
    print(paint("Settings: ", DIM)
          + label_for(UNITS, settings["units"]).split(" (")[0] + " | "
          + label_for(VEHICLES, settings["vehicle"]) + " | "
          + label_for(DETAILS, settings["detail"]).split(" (")[0]
          + paint("   (type s to change, q to quit)", DIM) + "\n")


# ---------- display ----------
def print_error(status, message):
    line = "Status Code: " + str(status) + "; " + message
    wrapped = textwrap.wrap(line, term_width() - 4) or [line]
    bar = "*" * (max(len(w) for w in wrapped) + 4)
    print(paint(bar, RED))
    for w in wrapped:
        print(paint("* " + w.ljust(len(bar) - 4) + " *", RED))
    print(paint(bar, RED) + "\n")


def print_box(rows):
    label_w = max(len(r[0]) for r in rows)
    inner_w = min(term_width() - 4, label_w + 2 + max(len(r[1]) for r in rows))
    value_w = inner_w - label_w - 2
    print("┌" + "─" * (inner_w + 2) + "┐")
    for label, value in rows:
        if len(value) > value_w:
            value = value[:value_w - 1] + "…"
        print("│ " + paint(label.ljust(label_w), BOLD_CYAN) + "  " + value.ljust(value_w) + " │")
    print("└" + "─" * (inner_w + 2) + "┘")


def print_summary(orig_label, dest_label, path):
    units = settings["units"]
    rows = [
        ("From", orig_label),
        ("To", dest_label),
        ("Travel mode", label_for(VEHICLES, settings["vehicle"])),
        ("Trip Duration", format_time(path["time"])),
        ("Kilometers" if units == "km" else "Miles", format_dist(path["distance"], units).split(" ")[0]),
    ]
    if settings["detail"] == "extra":
        steps = path.get("instructions", [])
        longest = max(steps, key=lambda s: s["distance"]) if steps else None
        rows.append(("Average speed", format_speed(path["distance"], path["time"], units)))
        rows.append(("Steps", str(len(steps))))
        if longest:
            rows.append(("Longest step", format_dist(longest["distance"], units) + " - " + longest["text"]))
    print_box(rows)

# added feature to show the user the directions of their destination

def print_table(instructions):
    units = settings["units"]
    rows = []
    for i, ins in enumerate(instructions, 1):
        is_finish = ins.get("sign") == 4  
        rows.append((str(i), ins["text"], format_dist(ins["distance"], units), is_finish))

    num_w = max(len("#"), len(str(len(rows))))
    dist_w = max(len("Distance"), max(len(r[2]) for r in rows))
    text_w = max(30, term_width() - num_w - dist_w - 10)

    def rule(left, mid, right):
        return left + "─" * (num_w + 2) + mid + "─" * (text_w + 2) + mid + "─" * (dist_w + 2) + right

    print(rule("┌", "┬", "┐"))
    print("│ " + cell("#", num_w, BOLD_CYAN) + " │ " + cell("Directions", text_w, BOLD_CYAN)
          + " │ " + cell("Distance", dist_w, BOLD_CYAN, "right") + " │")
    print(rule("├", "┼", "┤"))
    for n, (num, text, dist, is_finish) in enumerate(rows):
        lines = textwrap.wrap(text, text_w) or [""]
        text_code = GREEN if is_finish else None
        for j, line in enumerate(lines):
            print("│ " + cell(num if j == 0 else "", num_w, DIM, "right") + " │ "
                  + cell(line, text_w, text_code) + " │ "
                  + cell(dist if j == 0 else "", dist_w, YELLOW, "right") + " │")
        if n < len(rows) - 1:
            print(rule("├", "┼", "┤"))
    print(rule("└", "┴", "┘"))


def show_route(orig_label, dest_label, path):
    print_summary(orig_label, dest_label, path)
    if settings["detail"] != "summary":
        print_table(path["instructions"])
    print()


# ---------- main loop ----------
def main():
    print_settings()
    while True:
        orig = input(paint("Starting Location: ", CYAN)).strip()
        if orig.lower() in ("quit", "q"):
            break
        if orig.lower() == "s":
            settings_menu()
            continue
        dest = input(paint("Destination: ", CYAN)).strip()
        if dest.lower() in ("quit", "q"):
            break

        if not orig or not dest:
            print_error(611, "Missing an entry for one or both locations.")
            continue

        o_lat, o_lng, o_label, status, message = geocode(orig)
        if status != 200:
            print_error(status, "Could not find starting location. " + message)
            continue
        d_lat, d_lng, d_label, status, message = geocode(dest)
        if status != 200:
            print_error(status, "Could not find destination. " + message)
            continue

        params = {
            "point": [str(o_lat) + "," + str(o_lng), str(d_lat) + "," + str(d_lng)],
            "vehicle": settings["vehicle"],
            "locale": "en",
            "instructions": "true",
            "calc_points": "true",  
            "key": key,
        }
        resp = requests.get(ROUTE_URL, params=params)
        print(paint("URL: " + resp.url.replace(key, "your_api_key"), DIM)) 
        json_data = resp.json()

        if resp.status_code == 200:
            print(paint("API Status: " + str(resp.status_code) + " = A successful route call.\n", GREEN))
            show_route(o_label, d_label, json_data["paths"][0])
        elif resp.status_code == 400:
            print_error(resp.status_code, "Route not found or invalid input for this travel mode. "
                        + json_data.get("message", ""))
        elif resp.status_code == 401:
            print_error(resp.status_code, "Invalid or missing GraphHopper API key.")
        elif resp.status_code == 429:
            print_error(resp.status_code, "Daily API credit limit reached.")
        else:
            print_error(resp.status_code, "Refer to https://docs.graphhopper.com/ " + json_data.get("message", ""))


if __name__ == "__main__":
    main()