const _originalFetch = window.fetch.bind(window);

let _token: string | null = null;

/** Call this whenever the session changes to keep the token current. */
export function setAuthToken(token: string | null) {
  _token = token;
}

/**
 * Patches window.fetch once so every /api/* request carries the auth token.
 * The token is stored synchronously — no async lookup on every request.
 */
export function initAuthFetch() {
  window.fetch = (input, init) => {
    const url =
      typeof input === "string"
        ? input
        : input instanceof URL
        ? input.href
        : (input as Request).url;

    if (url.startsWith("/api") && _token) {
      init = {
        ...init,
        headers: {
          ...(init?.headers ?? {}),
          Authorization: `Bearer ${_token}`,
        },
      };
    }

    return _originalFetch(input, init);
  };
}

export function resetAuthFetch() {
  _token = null;
  window.fetch = _originalFetch;
}
