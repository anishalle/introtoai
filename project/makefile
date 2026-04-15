CAPTURE = uv run capture.py
PDB_CAPTURE = uv run python -m pdb capture.py

vsbase:
	$(CAPTURE) -r baselineTeam -b myTeam

base:
	$(CAPTURE)

self:
	$(CAPTURE) -r myTeam -b myTeam

int:
	$(CAPTURE) --keys0

debug:
	$(PDB_CAPTURE) -r baselineTeam -b myTeam

debugall:
	uv run tests/debug_capture.py --layout tinyCapture --all-agents --max-decisions 12
