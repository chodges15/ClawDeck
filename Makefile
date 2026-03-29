PYTHON ?= .venv/bin/python
DEVTOOLS := $(PYTHON) -m clawdeck.devtools
PYDOC_OUTPUT_DIR ?= docs/api
PYDOC_PACKAGE_MODULES := $(sort $(patsubst %.py,%,$(subst /,.,$(filter-out clawdeck/__init__.py,$(wildcard clawdeck/*.py)))))
PYDOC_MODULES := clawdeck main menubar install_hooks overlay $(PYDOC_PACKAGE_MODULES)

LABEL ?= TEST
BG ?= ffb000
FG ?= 000000
KEY ?= 0
BRIGHTNESS ?= 80
WAIT ?= 0

.PHONY: help docs-pydoc clean-pydoc util-iterm util-iterm-frontmost util-deck-list util-deck-clear util-deck-fill util-deck-key util-deck-demo

help:
	@echo "Documentation targets:"
	@echo "  make docs-pydoc"
	@echo "  make clean-pydoc"
	@echo ""
	@echo "Utility targets:"
	@echo "  make util-iterm"
	@echo "  make util-iterm-frontmost"
	@echo "  make util-deck-list"
	@echo "  make util-deck-clear BRIGHTNESS=80 WAIT=0"
	@echo "  make util-deck-fill LABEL=TEST BG=ffb000 FG=000000 BRIGHTNESS=80 WAIT=0"
	@echo "  make util-deck-key KEY=0 LABEL=T1 BG=ffb000 FG=000000 BRIGHTNESS=80 WAIT=0"
	@echo "  make util-deck-demo BRIGHTNESS=80 WAIT=0"

docs-pydoc:
	mkdir -p $(PYDOC_OUTPUT_DIR)
	rm -f $(PYDOC_OUTPUT_DIR)/*.html
	cd $(PYDOC_OUTPUT_DIR) && PYTHONPATH=$(CURDIR) $(CURDIR)/$(PYTHON) -m pydoc -w $(PYDOC_MODULES)
	$(CURDIR)/$(PYTHON) scripts/postprocess_pydoc.py
	touch docs/.nojekyll

clean-pydoc:
	rm -rf $(PYDOC_OUTPUT_DIR) docs/index.html docs/pydoc.css docs/.nojekyll

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
