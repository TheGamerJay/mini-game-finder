.PHONY: smoke
smoke:
	./smoke_test_api.sh $${BASE_URL:-http://localhost:5000}
