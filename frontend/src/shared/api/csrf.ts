// AI contribution: 50% or more AI-generated
/**
 * Django's CSRF token, read from its `csrftoken` cookie. Session-authenticated
 * writes (POST, PATCH, DELETE) must send it back in the X-CSRFToken header.
 */
export function csrfToken(): string | null {
  const prefix = "csrftoken=";
  const cookie = document.cookie.split("; ").find((part) => part.startsWith(prefix));
  return cookie ? decodeURIComponent(cookie.slice(prefix.length)) : null;
}
