.PHONY: hitl-demo review-demo test dry-run help

help:
	@echo "Targets:"
	@echo "  hitl-demo     Scan synthetic fixtures and write HITL outputs to out/"
	@echo "  review-demo   Generate BeCaps score findings for production review UI"
	@echo "  test          Run pytest"
	@echo "  dry-run       Run full scanner dry-run (BeCaps fixture)"

hitl-demo:
	python3 scripts/hitl_demo.py

review-demo:
	python3 scripts/review_demo.py

test:
	pytest tests/ -v

dry-run:
	python3 scripts/dry_run.py --company "TestCo"
