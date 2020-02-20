coverage-server:
	@cd coverage-report && python3 -m http.server 5000

.PHONY: test coverage-server
