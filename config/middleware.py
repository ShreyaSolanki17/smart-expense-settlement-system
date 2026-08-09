from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import AuthenticationFailed


class TokenAuthMiddleware:
    """Populate request.user from the same `Authorization: Token <key>`
    header the REST API uses (rest_framework.authentication.TokenAuthentication),
    so non-DRF views (GraphQL) share one auth mechanism instead of a second
    implementation. Session-authenticated requests are left untouched.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.authenticator = TokenAuthentication()

    def __call__(self, request):
        if not request.user.is_authenticated:
            try:
                result = self.authenticator.authenticate(request)
            except AuthenticationFailed:
                result = None
            if result is not None:
                request.user, _ = result
        return self.get_response(request)
