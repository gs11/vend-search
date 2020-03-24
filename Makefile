clean:
	rm -rf node_modules

deploy:
	npm install && \
	sls deploy

.PHONY: clean deploy