// The Content-Security-Policy is really enforced: inline scripts, inline styles and connections to other sites are blocked.
T.run(async () => {
  await T.wait(1500);
  const violations = [];
  document.addEventListener("securitypolicyviolation", (e) => violations.push(e.violatedDirective));
  const before = T.errors.length;

  window.__injected = false;
  const script = document.createElement("script"); script.textContent = "window.__injected = true"; document.body.append(script);
  await T.wait(100);
  T.check("an inline script does not run", window.__injected === false);

  document.body.setAttribute("style", "background: red");
  await T.wait(100);
  T.check("an inline style attribute is refused", violations.some((v) => v.startsWith("style-src")), violations.join(","));
  document.body.removeAttribute("style");

  let reached = true;
  try { await fetch("https://example.com/", { mode: "no-cors" }); } catch (e) { reached = false; }
  await T.wait(200);                                          // the policy report arrives a moment after the failed request
  T.check("the page cannot connect to another site", reached === false && violations.some((v) => v.startsWith("connect-src")), violations.join(","));

  const frame = document.createElement("iframe"); frame.src = "https://example.com/"; document.body.append(frame);
  await T.wait(200);
  T.check("the page cannot embed another site", violations.some((v) => v.startsWith("frame-src") || v.startsWith("default-src")), violations.join(","));
  frame.remove();

  T.errors.splice(before);                                   // the violations above were on purpose: they are not test failures
  const headers = await fetch("/").then((r) => Object.fromEntries(r.headers.entries()));
  T.check("the page is served with the policy header", /default-src 'self'/.test(headers["content-security-policy"] || ""));
});
