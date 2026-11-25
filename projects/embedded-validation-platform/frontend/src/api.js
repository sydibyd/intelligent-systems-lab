let token = '';
export function setToken(value) { token = value.trim(); }
export async function apiFetch(path, options = {}) {
  if (typeof path !== 'string' || !path.startsWith('/api/')) throw Error('Invalid API path');
  const headers = new Headers(options.headers || {});
  if (token) headers.set('Authorization', 'Bearer ' + token);
  return fetch(path, {...options, headers, redirect: 'error'});
}
