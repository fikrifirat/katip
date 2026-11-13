# Photographed, hand-filled forms

Lawyers attach phone photos of hand-filled lease contracts (kira sözleşmesi) to filings at the sulh hukuk
courts, and these are the documents KVKK has fined lawyers over. The first real one we were sent leaked
both TC kimlik numbers and both names through Katip Tiny. Real ones cannot be shared, so this folder makes
look-alikes and scores masking on them without OCR.

```
python lab/photo_forms/make_photo_forms.py /tmp/photo --n 12          # PDFs + answer keys
node src/tests/test_photo_forms.mjs /tmp/photo                       # street-visible addresses (default)
node src/tests/test_photo_forms.mjs /tmp/photo --address full        # whole addresses
```

Each form: our own printed layout (not a copy of any stationery form), values in one of five OFL
handwriting fonts (downloaded from github.com/google/fonts into `fonts/` on first run) in ballpoint blue,
then a phone-photo look: wooden floor, perspective, uneven light, show-through from the back of the sheet,
blur, JPEG, saved as a 1152x2048 pt PDF page the way an iPhone saves a photo. Names, ID numbers (valid
checksum) and addresses are made up; streets are named after people (Alparslan Türkeş, Fevzi Çakmak ...)
because those must stay readable.

The answer key holds every value's box on the final page:

* `entities`: what must be masked (both parties' names and TC kimlik numbers, the building/block/door part
  of both home addresses, the names in the signature block). Leaked = masks cover < 70% of the box.
* `visible`: what must stay readable (mahalle and street of the leased property and of both home addresses,
  district/province). Over-masked = masks cover > 30% of the box.

Limits: fonts are neater than real handwriting and the ink is bluer than many real pens, so this set is
easier for the pen-colour signal and harder for Tesseract than the one real photo we have. Use it to
compare pipelines, not as a promise about real documents.
