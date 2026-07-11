# Build OMNI-RANK documentation PDFs.
#
# Requires: pandoc + weasyprint (pip install weasyprint)
# Usage:
#   make            # build both PDFs
#   make features   # only FEATURES.pdf
#   make tests      # only TEST_SCENARIOS.pdf
#   make clean

PANDOC ?= pandoc
ENGINE ?= weasyprint
CSS    := print.css

FEATURES_MD := FEATURES.md
TESTS_MD    := TEST_SCENARIOS.md

FEATURES_PDF := FEATURES.pdf
TESTS_PDF    := TEST_SCENARIOS.pdf

PANDOC_OPTS := \
	--from=markdown+raw_html+pipe_tables+yaml_metadata_block \
	--pdf-engine=$(ENGINE) \
	--css=$(CSS) \
	--standalone

.PHONY: all features tests clean
all: features tests

features: $(FEATURES_PDF)
tests:    $(TESTS_PDF)

$(FEATURES_PDF): $(FEATURES_MD) $(CSS)
	$(PANDOC) $(PANDOC_OPTS) $< -o $@

$(TESTS_PDF): $(TESTS_MD) $(CSS)
	$(PANDOC) $(PANDOC_OPTS) $< -o $@

clean:
	rm -f $(FEATURES_PDF) $(TESTS_PDF)
