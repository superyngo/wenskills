// skills/wens-tutor/web/app/api.js
const base = "";
async function req(method, path, body) {
  const res = await fetch(base + path, {
    method,
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(method + " " + path + " -> " + res.status);
  return res.json();
}
export const get = (p) => req("GET", p);
export const post = (p, b) => req("POST", p, b || {});
export const put = (p, b) => req("PUT", p, b || {});
export const patch = (p, b) => req("PATCH", p, b || {});
export const del = (p) => req("DELETE", p);
