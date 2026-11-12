# Security policy

## Supported versions

Only the latest release on `main` and the live demo at https://shopsmart.sytnik-studio.com receive security fixes.

## Reporting a vulnerability

Please don't open a public issue. Email **ivan.sytnik02@gmail.com** with:

- what is affected (API endpoint, frontend page, price scanner) and the version or commit;
- steps to reproduce, or a proof of concept;
- the impact you expect (e.g. bypassing the rate limit or daily cap, leaking the OpenAI key or server errors, XSS through share links).

You'll get a reply within 72 hours. Please give a reasonable time for a fix before you disclose the issue publicly. Test only against your own local instance, not the live demo: requests to `POST /generate` cost real OpenAI credit.

Built-in protections (CSP, rate limit, daily cap, input bounds, generic errors) are listed in the README under [Security](README.md#security).
