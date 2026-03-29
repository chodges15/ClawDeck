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
	@printf '%s\n' \
	'<!DOCTYPE html>' \
	'<html lang="en">' \
	'<head>' \
	'  <meta charset="utf-8">' \
	'  <meta name="viewport" content="width=device-width, initial-scale=1">' \
	'  <title>ClawDeck API Docs</title>' \
	'  <style>' \
	'    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 3rem auto; max-width: 48rem; padding: 0 1.5rem; line-height: 1.5; }' \
	'    h1 { margin-bottom: 0.5rem; }' \
	'    ul { padding-left: 1.25rem; }' \
	'  </style>' \
	'</head>' \
	'<body>' \
	'  <h1>ClawDeck API Docs</h1>' \
	'  <p>Generated with <code>make docs-pydoc</code>.</p>' \
	'  <ul>' \
	'    <li><a href="api/clawdeck.html">Package overview</a></li>' \
	'    <li><a href="api/clawdeck.controller.html">Controller module</a></li>' \
	'    <li><a href="api/clawdeck.devtools.html">Developer tools</a></li>' \
	'    <li><a href="api/main.html">CLI entrypoint</a></li>' \
	'  </ul>' \
	'</body>' \
	'</html>' > docs/index.html
	touch docs/.nojekyll

clean-pydoc:
	rm -rf $(PYDOC_OUTPUT_DIR) docs/index.html docs/.nojekyll

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
