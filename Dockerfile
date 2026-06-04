# Small runtime image for the web crawler CLI.
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Copy only what the package build needs (good layer caching). lxml ships
# manylinux wheels, so no C toolchain is required at build time.
COPY pyproject.toml README.md ./
COPY webcrawler ./webcrawler
RUN pip install .

# Drop root for runtime.
RUN useradd --create-home --uid 1000 crawler
USER crawler
WORKDIR /home/crawler

ENTRYPOINT ["webcrawler"]
CMD ["--help"]
