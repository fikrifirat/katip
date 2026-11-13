// Site settings. Edit, then re-run build_site.py (it also writes the page's CSP from these).
export default {
  // "Hata bildir" opens an e-mail draft to this address. Public on the site: expect some spam.
  reportEmail: "fikrifirat@gmail.com",
  // Optional auto-send: a form service URL that accepts multipart POST with a file
  // (e.g. a Formspree form "https://formspree.io/f/xxxxxxx"). Empty = e-mail draft only.
  // Setting it adds that one origin to the CSP; reports then travel through that service.
  reportEndpoint: "",
  // Credit line added to redacted PDF, image, Word and text output when "Filigran" is ticked.
  // Keep the text ASCII: it is drawn with a standard PDF font.
  watermark: {
    text: { tr: "Katip Mask ile maskelendi - fikrifirat.github.io/katip", en: "Redacted with Katip Mask - fikrifirat.github.io/katip" },
    url: "https://fikrifirat.github.io/katip/",
  },
};
