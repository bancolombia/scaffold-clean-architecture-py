"""Pipeline provider registry."""

from __future__ import annotations

from pathlib import PurePosixPath

from scaffold_ca_python.factory.pipelines.pipeline_factory import PipelineFactory

PIPELINE_PROVIDERS: dict[str, PipelineFactory] = {
    "github": PipelineFactory(
        PurePosixPath(".github/workflows/ci.yml"),
        "pipeline/github/ci.yml.jinja2",
        "ci.yml",
    ),
    "azure": PipelineFactory(
        PurePosixPath("azure-pipelines.yml"),
        "pipeline/azure/azure_pipelines.yml.jinja2",
        "azure-pipelines.yml",
    ),
}
