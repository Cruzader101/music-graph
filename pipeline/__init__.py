"""Music-graph pipeline package.

Hard stage boundaries (music-project.md): fetch → clean → features → similarity →
export. Stages communicate only through cache.db and files in data/derived/;
they never import another stage's internals. Shared infrastructure (config,
identity, cache, api clients) is not a stage and may be imported freely.
"""
