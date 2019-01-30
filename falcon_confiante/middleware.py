import falcon
from jsonschema import FormatChecker
from jsonschema.validators import Draft4Validator
from jsonschema.exceptions import ValidationError


class OpenApiAuthenticationMiddleware(object):

    __slots__ = ("openapi_spec", "auth_fn", "default_security_schemes", "strict_mode")

    def __init__(self, openapi_spec: dict, auth_fn, strict_mode: bool = True):
        self.openapi_spec = openapi_spec
        self.auth_fn = auth_fn
        self.default_security_schemes = openapi_spec.get("security")
        self.strict_mode = strict_mode

    def process_resource(self, req, resp, resource, params):
        path, http_method = req.uri_template, req.method.lower()

        try:
            security_schema = self.openapi_spec["paths"][path][http_method].get(
                "security", self.default_security_schemes
            )

            if security_schema:
                user = self.auth_fn(req, resp, resource, params)
                if user is None:
                    raise OpenApiAutheticationError(falcon.HTTP_UNAUTHORIZED)

                req.context["user"] = user
        except KeyError as exc:
            if not self.strict_mode:
                return
            raise RuntimeError(
                f"Error {http_method.upper()} {path} not defined in Open API spec"
            ) from exc


class OpenApiSchemaValidationMiddleware(object):

    DEFAULT_CONTENT_TYPE = "application/json"

    __slots__ = (
        "openapi_spec",
        "format_checker",
        "validators",
        "strict_mode",
        "validate_response",
    )

    def __init__(
        self,
        openapi_spec: dict,
        strict_mode: bool = True,
        validate_response: bool = False,
    ):
        self.openapi_spec = openapi_spec
        self.format_checker = FormatChecker()
        self.validators = {}
        self.strict_mode = strict_mode
        self.validate_response = validate_response

    def process_resource(self, req, resp, resource, params):
        path, http_method = req.uri_template, req.method.lower()

        try:
            validator = self.get_validator_for_request_body(path, http_method)
            if validator:
                errors = [
                    self._format_validation_error(err)
                    for err in validator.iter_errors(req.media)
                ]

                if errors:
                    raise OpenApiSchemaError(falcon.HTTP_BAD_REQUEST, errors)
        except KeyError as exc:
            if not self.strict_mode:
                return
            raise RuntimeError(
                f"Error {http_method.upper()} {path} not defined in Open API spec"
            ) from exc

    def process_response(self, req, resp, resource, req_succeeded):
        if self.validate_response is False:
            return

        if req.uri_template is None:
            return  # not route matched

        handler = resp.options.media_handlers.find_by_media_type(
            resp.content_type, resp.options.default_media_type
        )

        media = resp.media
        if media is None and not req_succeeded:
            # falcon HTTP errors not set response.media property!
            media = handler.deserialize(resp.body.encode("utf-8"))

        path, http_method, status_code = (
            req.uri_template,
            req.method.lower(),
            resp.status[:3],
        )
        if path is None:
            return  # not route matched!

        try:
            response_payload = handler.serialize(media)

            validator = self.get_validator_for_response(path, http_method, status_code)
            errors = [
                self._format_validation_error(err)
                for err in validator.iter_errors(handler.deserialize(response_payload))
            ]
            if errors:
                raise OpenApiSchemaError(OpenApiSchemaError.HTTP_RESPONSE_ERROR, errors)
        except KeyError as exc:
            if not self.strict_mode:
                return
            raise RuntimeError(
                f"Error {http_method.upper()} {path} -> {status_code} response not defined in Open API spec"
            ) from exc

    def get_validator_for_request_body(self, path, http_method):
        if (path, http_method) not in self.validators:
            request_body = self.openapi_spec["paths"][path][http_method].get(
                "requestBody"
            )
            validator = None
            if request_body:
                schema = request_body["content"][self.DEFAULT_CONTENT_TYPE]["schema"]
                validator = Draft4Validator(schema, format_checker=self.format_checker)
            self.validators[(path, http_method)] = validator

        return self.validators[(path, http_method)]

    def get_validator_for_response(self, path, http_method, status_code):
        if (path, http_method, status_code) not in self.validators:
            response = self.openapi_spec["paths"][path][http_method]["responses"][
                status_code
            ]

            schema = response["content"][self.DEFAULT_CONTENT_TYPE]["schema"]
            validator = Draft4Validator(schema, format_checker=self.format_checker)

            self.validators[(path, http_method, status_code)] = validator

        return self.validators[(path, http_method, status_code)]

    def _format_validation_error(self, err):
        return {
            "message": err.message,
            "field": f'.{".".join(map(str, err.absolute_path))}',
        }


class OpenApiError(falcon.HTTPError):
    def __init__(self, status, errors=None, **kwargs):
        super().__init__(status, **kwargs)
        self.errors = errors

    def to_dict(self, obj_type=dict):
        obj = obj_type()
        obj["message"] = self.title
        if self.errors:
            obj["errors"] = self.errors
        return obj


class OpenApiAutheticationError(OpenApiError):
    pass


class OpenApiSchemaError(OpenApiError):

    HTTP_RESPONSE_ERROR = "593 Bad Response"
