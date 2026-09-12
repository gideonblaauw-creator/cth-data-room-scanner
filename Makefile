.PHONY: hitl-demo test dry-run help hitl-static-serve hitl-host-url

help:
	@echo "Targets:"
	@echo "  hitl-demo          Scan synthetic fixtures and write HITL outputs to out/"
	@echo "  hitl-static-serve  Serve microworld static files on :8765"
	@echo "  hitl-host-url      Print stable public microworld URL from docs"
	@echo "  test               Run pytest"
	@echo "  dry-run            Run full scanner dry-run (BeCaps fixture)"

HITL_STATIC_PORT ?= 8765

hitl-static-serve:
	@echo "Microworld static host → http://127.0.0.1:$(HITL_STATIC_PORT)/"
	@echo "Review demo (optional) → python3 -m http.server 8766 --directory hitl/review-static"
	python3 -m http.server $(HITL_STATIC_PORT) --directory hitl/microworld

hitl-host-url:
	@grep -m1 '^\*\*Production:\*\*' hitl/STABLE-HOST.md | sed 's/.*\*\*Production:\*\* //' || echo "NEED_LOGIN — see hitl/STABLE-HOST.md"

hitl-demo:
	python3 scripts/hitl_demo.py

test:
	pytest tests/ -v

dry-run:
	python3 scripts/dry_run.py --company "TestCo"
