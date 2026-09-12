.PHONY: hitl-demo langgraph-dogfood test dry-run help

help:
	@echo "Targets:"
	@echo "  hitl-demo          Scan synthetic fixtures and write HITL outputs to out/"
	@echo "  langgraph-dogfood  LangGraph HITL interrupt smoke (--auto-resume)"
	@echo "  test               Run pytest"
	@echo "  dry-run            Run full scanner dry-run (BeCaps fixture)"

hitl-demo:
	python3 scripts/hitl_demo.py

langgraph-dogfood:
	python3 scripts/langgraph_dogfood.py start --auto-resume

test:
	pytest tests/ -v

dry-run:
	python3 scripts/dry_run.py --company "TestCo"
