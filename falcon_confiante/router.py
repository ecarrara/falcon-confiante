import importlib
from collections import defaultdict
import falcon
from falcon.routing.compiled import CompiledRouter


_falcon_version = [int(d) for d in falcon.__version__.split('.')]


class OpenApiRouter(CompiledRouter):

    __slots__ = ("root_package", "resources", "strict_mode", "mapping")

    def __init__(self, package, openapi_spec: dict, strict_mode: bool = True):
        super().__init__()

        self.root_package = package
        self.resources = {}
        self.strict_mode = True
        self.mapping = defaultdict(lambda: {})  # resource -> method -> fn

        for path, http_methods in openapi_spec["paths"].items():
            for http_method, defn in http_methods.items():
                operationId = defn.get("operationId")
                if operationId is None:
                    if not self.strict_mode:
                        continue

                    raise RuntimeError(
                        f"No `operationId` specified in endpoint {http_method.upper()} {path}"
                    )

                try:
                    module_class, method_name = operationId.split("::", 1)
                    module, class_ = module_class.rsplit(".", 1)

                    resource = self.get_resource(module, class_)
                    method = getattr(resource, method_name)

                    self.mapping[resource][http_method.upper()] = method
                except (AttributeError, ModuleNotFoundError) as exc:
                    raise RuntimeError(
                        f"Error registering endpoint {http_method.upper()} {path}: {exc}"
                    )

            for resource, method_map in self.mapping.items():
                if _falcon_version[0] >= 2:
                    self.add_route(path, resource)
                else:
                    self.add_route(path, self.mapping[resource], resource)

    # override custom mapping strategy
    def map_http_methods(self, resource, **kwargs):
        # falcon >= 2 only
        return self.mapping[resource]

    def get_resource(self, module, class_):
        if (module, class_) not in self.resources:
            self.resources[(module, class_)] = self.instantiate_resource(module, class_)
        return self.resources[(module, class_)]

    def instantiate_resource(self, module, class_):
        module = importlib.import_module(module, self.root_package)
        Class = getattr(module, class_)
        return Class()
