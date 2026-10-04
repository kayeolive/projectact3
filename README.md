# projectact3

A Python program that uses the MapQuest Directions API to show the trip duration, distance, fuel used, and turn-by-turn directions between two locations.

## Team
| Member | Role |
| Olive Kaye R. Reforba | Scrum Leader and GitHub Admin |
| Christian Kaide T. Estremos | Developer: Output and UI |
| Christian Angelyn H. Nicodemus | Developer: New Options |
| JC Dre Gabriel V. Ledonio | QA, Documentation, and Backlog |


## How to run
1. Install Python 3 and the requests library: `pip install requests`
2. Get a free API key from developer.mapquest.com
3. In `mapquest_directions.py`, replace `your_api_key` with your key (never commit your real key)
4. Run: `python mapquest_directions.py`
5. Type a starting location and a destination. Type `quit` or `q` to exit.

## Branching strategy
- `main`: final, protected code. Changes only through pull requests.
- `dev`: where finished work is combined and tested.
- `feature/<name>-<task>`: one branch per member per task.
