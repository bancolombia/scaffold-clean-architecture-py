"""Layer enum and FORBIDDEN_IMPORTS dependency mapping."""

from enum import StrEnum


class Layer(StrEnum):
    DOMAIN_MODEL = "domain/model"
    DOMAIN_USECASE = "domain/usecase"
    ENTRY_POINTS = "infrastructure/entry_points"
    DRIVEN_ADAPTERS = "infrastructure/driven_adapters"
    HELPERS = "infrastructure/helpers"
    APPLICATION = "application"


# For each layer, packages under the listed layers must not be imported.
# APPLICATION is omitted: it may depend on any layer.
FORBIDDEN_IMPORTS: dict[Layer, list[Layer]] = {
    Layer.DOMAIN_MODEL: [
        Layer.DOMAIN_USECASE,
        Layer.ENTRY_POINTS,
        Layer.DRIVEN_ADAPTERS,
        Layer.HELPERS,
        Layer.APPLICATION,
    ],
    Layer.DOMAIN_USECASE: [
        Layer.ENTRY_POINTS,
        Layer.DRIVEN_ADAPTERS,
        Layer.HELPERS,
        Layer.APPLICATION,
    ],
    Layer.ENTRY_POINTS: [
        Layer.APPLICATION,
    ],
    Layer.DRIVEN_ADAPTERS: [
        Layer.APPLICATION,
    ],
    Layer.HELPERS: [
        Layer.APPLICATION,
    ],
    Layer.APPLICATION: [],
}
