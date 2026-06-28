agent:
	@python -m app.agent.main

warmup:
	@python -m app.warmup.main

.PHONY: agent warmup
