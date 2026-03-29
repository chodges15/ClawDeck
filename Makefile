PYTHON ?= .venv/bin/python
DEVTOOLS := $(PYTHON) -m clawdeck.devtools

LABEL ?= TEST
BG ?= ffb000
FG ?= 000000
KEY ?= 0
BRIGHTNESS ?= 80
WAIT ?= 0

.PHONY: help util-iterm util-iterm-frontmost util-deck-list util-deck-clear util-deck-fill util-deck-key util-deck-demo

help:
	@echo "Utility targets:"
	@echo "  make util-iterm"
	@echo "  make util-iterm-frontmost"
	@echo "  make util-deck-list"
	@echo "  make util-deck-clear BRIGHTNESS=80 WAIT=0"
	@echo "  make util-deck-fill LABEL=TEST BG=ffb000 FG=000000 BRIGHTNESS=80 WAIT=0"
	@echo "  make util-deck-key KEY=0 LABEL=T1 BG=ffb000 FG=000000 BRIGHTNESS=80 WAIT=0"
	@echo "  make util-deck-demo BRIGHTNESS=80 WAIT=0"

util-iterm:
	$(DEVTOOLS) iterm info

util-iterm-frontmost:
	$(DEVTOOLS) iterm frontmost

util-deck-list:
	$(DEVTOOLS) deck list

util-deck-clear:
	$(DEVTOOLS) deck clear --brightness $(BRIGHTNESS) --wait $(WAIT)

util-deck-fill:
	$(DEVTOOLS) deck fill --label "$(LABEL)" --bg "$(BG)" --fg "$(FG)" --brightness $(BRIGHTNESS) --wait $(WAIT)

util-deck-key:
	$(DEVTOOLS) deck key --key $(KEY) --label "$(LABEL)" --bg "$(BG)" --fg "$(FG)" --brightness $(BRIGHTNESS) --wait $(WAIT)

util-deck-demo:
	$(DEVTOOLS) deck demo --brightness $(BRIGHTNESS) --wait $(WAIT)
