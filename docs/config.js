// Site settings. Edit, then re-run build.py (it also writes the page's CSP from these).
export default {
  // "Hata bildir" opens an e-mail draft to this address. Public on the site: expect some spam.
  reportEmail: "fikrifirat@gmail.com",
  // Optional auto-send: a form service URL that accepts multipart POST with a file
  // (e.g. a Formspree form "https://formspree.io/f/xxxxxxx"). Empty = e-mail draft only.
  // Setting it adds that one origin to the CSP; reports then travel through that service.
  reportEndpoint: "",
};
