import importlib
from collections import defaultdict
from falcon.routing.compiled import CompiledRouter


class OpenApiRouter(CompiledRouter):

    __slots__ = ("root_package", "resources", "strict_mode")

    def __init__(self, package, openapi_spec: dict, strict_mode: bool = True):
        super().__init__()

        self.root_package = package
        self.resources = {}
        self.strict_mode = True

        for path, http_methods in openapi_spec["paths"].items():
            mapping = defaultdict(lambda: defaultdict(lambda: {}))

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

                    mapping[resource][http_method.upper()] = method
                except (AttributeError, ModuleNotFoundError) as exc:
                    raise RuntimeError(
                        f"Error registering endpoint {http_method.upper()} {path}: {exc}"
                    )

            for resource, method_map in mapping.items():
                self.add_route(path, method_map, resource)

    def get_resource(self, module, class_):
        if (module, class_) not in self.resources:
            self.resources[(module, class_)] = self.instantiate_resource(module, class_)
        return self.resources[(module, class_)]

    def instantiate_resource(self, module, class_):
        module = importlib.import_module(module, self.root_package)
        Class = getattr(module, class_)
        return Class()
